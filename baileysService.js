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
let connectionStatus = 'DISCONNECTED'; // DISCONNECTED, CONNECTING, CONNECTED
let isConnecting = false;

const authFolder = path.join(__dirname, 'baileys_auth_info');
if (!fs.existsSync(authFolder)) {
    fs.mkdirSync(authFolder, { recursive: true });
}

async function startBaileysEngine(onMessageReceivedCallback) {
    if (isConnecting || connectionStatus === 'CONNECTED') {
        return;
    }

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
            browser: ['MaintAgent', 'Chrome', '1.0.0']
        });

        waSock.ev.on('creds.update', saveCreds);

        waSock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;

            if (qr) {
                try {
                    currentQRCodeDataUrl = await QRCode.toDataURL(qr);
                    connectionStatus = 'QR_READY';
                    console.log('[Baileys] New WhatsApp QR Code generated for scanning.');
                } catch (err) {
                    console.error('[Baileys] Error rendering QR Code:', err);
                }
            }

            if (connection === 'close') {
                isConnecting = false;
                const statusCode = lastDisconnect?.error?.output?.statusCode;
                const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
                console.log(`[Baileys] Connection closed due to: ${lastDisconnect?.error}. Reconnecting: ${shouldReconnect}`);
                
                if (shouldReconnect) {
                    connectionStatus = 'RECONNECTING';
                    setTimeout(() => startBaileysEngine(onMessageReceivedCallback), 3000);
                } else {
                    connectionStatus = 'DISCONNECTED';
                    currentQRCodeDataUrl = null;
                    // Clear auth if logged out
                    if (fs.existsSync(authFolder)) {
                        fs.rmSync(authFolder, { recursive: true, force: true });
                    }
                }
            } else if (connection === 'open') {
                isConnecting = false;
                connectionStatus = 'CONNECTED';
                currentQRCodeDataUrl = null;
                console.log('[Baileys] 🟢 WhatsApp Web session connected successfully!');
            }
        });

        waSock.ev.on('messages.upsert', async ({ messages, type }) => {
            if (type !== 'notify') return;

            for (const msg of messages) {
                if (msg.key.fromMe) continue; // Ignore self messages

                const fromJid = msg.key.remoteJid;
                if (!fromJid || fromJid.endsWith('@g.us')) continue; // Ignore group chats for now or support direct chats

                const text = msg.message?.conversation || 
                             msg.message?.extendedTextMessage?.text || 
                             '';

                if (!text.trim()) continue;

                const senderPhone = fromJid.replace('@s.whatsapp.net', '');
                const senderName = msg.pushName || 'WhatsApp User';

                console.log(`[Baileys] Incoming message from ${senderPhone} (${senderName}): "${text}"`);

                if (onMessageReceivedCallback) {
                    try {
                        const replyText = await onMessageReceivedCallback(text, senderPhone, senderName);
                        if (replyText && waSock) {
                            await waSock.sendMessage(fromJid, { text: replyText });
                            console.log(`[Baileys] Reply sent to ${senderPhone}`);
                        }
                    } catch (err) {
                        console.error('[Baileys] Error handling message callback:', err);
                    }
                }
            }
        });

    } catch (err) {
        isConnecting = false;
        connectionStatus = 'DISCONNECTED';
        console.error('[Baileys] Error initializing socket:', err);
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
