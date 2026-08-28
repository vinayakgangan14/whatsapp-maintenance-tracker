const { 
    default: makeWASocket, 
    useMultiFileAuthState, 
    DisconnectReason, 
    fetchLatestBaileysVersion 
} = require('@whiskeysockets/baileys');
const QRCode = require('qrcode');
const pino = require('pino');
const path = require('path');
const fs = require('fs');

let waSock = null;
let currentQRCodeDataUrl = null;
let connectionStatus = 'DISCONNECTED'; // DISCONNECTED, CONNECTING, QR_READY, CONNECTED, RECONNECTING
let isConnecting = false;
let messageCallback = null;

const authFolder = path.join(__dirname, 'baileys_auth_info');

// ----------------------------------------------------------
// CREDENTIAL PERSISTENCE via Environment Variable
// Render wipes local files on restart, so we save auth state
// to the BAILEYS_AUTH_CREDS_JSON env var instruction (printed
// to console so you can copy it into Render env vars).
// ----------------------------------------------------------
function ensureAuthFolder() {
    if (!fs.existsSync(authFolder)) {
        fs.mkdirSync(authFolder, { recursive: true });
    }
}

function loadCredsFromEnv() {
    const envJson = process.env.BAILEYS_AUTH_CREDS_JSON;
    if (!envJson) return;
    ensureAuthFolder();
    try {
        const creds = JSON.parse(envJson);

        // Check if the saved session was never fully registered
        // (registered:false means QR scan was incomplete)
        const credsFile = creds['creds.json'];
        if (credsFile && credsFile.registered === false) {
            console.log('[Baileys] ⚠️ Saved credentials have registered:false — session was never completed. Starting fresh QR scan.');
            // Clear any stale files
            if (fs.existsSync(authFolder)) {
                fs.rmSync(authFolder, { recursive: true, force: true });
            }
            return; // Don't load bad creds — will show fresh QR
        }

        // Write each key as a separate file (Baileys multi-file auth format)
        for (const [filename, content] of Object.entries(creds)) {
            const filePath = path.join(authFolder, filename);
            fs.writeFileSync(filePath, typeof content === 'string' ? content : JSON.stringify(content), 'utf8');
        }
        console.log('[Baileys] ✅ Loaded WhatsApp auth credentials from environment variable.');
    } catch (e) {
        console.error('[Baileys] Failed to parse BAILEYS_AUTH_CREDS_JSON:', e.message);
    }
}

function printCredsToConsole() {
    // Bundle auth folder files into a single JSON and print it so
    // the user can copy it as an env var into Render.
    if (!fs.existsSync(authFolder)) return;
    const files = fs.readdirSync(authFolder);
    if (!files.length) return;
    const bundle = {};
    for (const file of files) {
        const filePath = path.join(authFolder, file);
        try {
            bundle[file] = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        } catch {
            bundle[file] = fs.readFileSync(filePath, 'utf8');
        }
    }
    console.log('\n[Baileys] ======= COPY THIS TO RENDER ENV VARS =======');
    console.log('Key:   BAILEYS_AUTH_CREDS_JSON');
    console.log('Value: ' + JSON.stringify(bundle));
    console.log('[Baileys] ====================================================\n');
}

// ----------------------------------------------------------
// CORE ENGINE
// ----------------------------------------------------------
async function startBaileysEngine(onMessageReceivedCallback) {
    if (onMessageReceivedCallback) {
        messageCallback = onMessageReceivedCallback;
    }

    if (isConnecting || connectionStatus === 'CONNECTED') {
        return;
    }

    // On first run: try restoring creds from env var
    loadCredsFromEnv();
    ensureAuthFolder();

    isConnecting = true;
    connectionStatus = 'CONNECTING';

    try {
        const { state, saveCreds } = await useMultiFileAuthState(authFolder);
        const { version } = await fetchLatestBaileysVersion();

        waSock = makeWASocket({
            version,
            logger: pino({ level: 'silent' }),
            printQRInTerminal: false,
            auth: state,
            browser: ['Pure Bot', 'Chrome', '1.0.0'],
            connectTimeoutMs: 60000,
            defaultQueryTimeoutMs: 60000,
            keepAliveIntervalMs: 25000
        });

        waSock.ev.on('creds.update', async () => {
            await saveCreds();
            // Print updated creds bundle so user can refresh Render env var
            printCredsToConsole();
        });

        waSock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;

            if (qr) {
                try {
                    currentQRCodeDataUrl = await QRCode.toDataURL(qr);
                    connectionStatus = 'QR_READY';
                    console.log('[Baileys] 📱 New WhatsApp QR Code ready. Open the dashboard QR tab to scan.');
                } catch (err) {
                    console.error('[Baileys] Error rendering QR Code:', err);
                }
            }

            if (connection === 'close') {
                isConnecting = false;
                const statusCode = lastDisconnect?.error?.output?.statusCode;
                const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
                console.log(`[Baileys] Connection closed (code=${statusCode}). Reconnect: ${shouldReconnect}`);

                if (shouldReconnect) {
                    connectionStatus = 'RECONNECTING';
                    // Exponential-like back-off: first retry after 5s
                    setTimeout(() => startBaileysEngine(null), 5000);
                } else {
                    connectionStatus = 'DISCONNECTED';
                    currentQRCodeDataUrl = null;
                    // Clear auth only on explicit logout
                    if (fs.existsSync(authFolder)) {
                        fs.rmSync(authFolder, { recursive: true, force: true });
                    }
                    console.log('[Baileys] 🔴 Logged out. Scan QR again to reconnect.');
                }
            } else if (connection === 'open') {
                isConnecting = false;
                connectionStatus = 'CONNECTED';
                currentQRCodeDataUrl = null;
                console.log('[Baileys] 🟢 WhatsApp CONNECTED! Pure Bot is online.');
                // Print creds so user can save them to Render env
                printCredsToConsole();
            }
        });

        waSock.ev.on('messages.upsert', async ({ messages, type }) => {
            if (type !== 'notify') return;

            for (const msg of messages) {
                if (msg.key.fromMe) continue;

                const fromJid = msg.key.remoteJid;
                if (!fromJid || fromJid.endsWith('@g.us')) continue;

                const text = msg.message?.conversation ||
                             msg.message?.extendedTextMessage?.text ||
                             '';

                if (!text.trim()) continue;

                const senderPhone = fromJid.replace('@s.whatsapp.net', '');
                const senderName = msg.pushName || 'WhatsApp User';

                console.log(`[Baileys] 📩 Incoming from ${senderPhone} (${senderName}): "${text}"`);

                const cb = messageCallback || onMessageReceivedCallback;
                if (cb) {
                    try {
                        const replyText = await cb(text, senderPhone, senderName);
                        if (replyText && waSock) {
                            await waSock.sendMessage(fromJid, { text: replyText });
                            console.log(`[Baileys] ✉️ Reply sent to ${senderPhone}`);
                        }
                    } catch (err) {
                        console.error('[Baileys] Error in message handler:', err);
                    }
                }
            }
        });

    } catch (err) {
        isConnecting = false;
        connectionStatus = 'DISCONNECTED';
        console.error('[Baileys] Fatal error initializing socket:', err);
        // Retry after 10s on unexpected errors
        setTimeout(() => startBaileysEngine(null), 10000);
    }
}

function getBaileysStatus() {
    return {
        status: connectionStatus,
        qrCode: currentQRCodeDataUrl
    };
}

module.exports = {
    startBaileysEngine,
    getBaileysStatus
};
