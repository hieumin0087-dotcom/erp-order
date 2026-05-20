const net = require('net');

const LISTEN_PORT = 8080;
const TARGET_HOST = '127.0.0.1';
const TARGET_PORT = 18789;

const server = net.createServer((clientSocket) => {
    const targetSocket = new net.Socket();
    
    targetSocket.connect(TARGET_PORT, TARGET_HOST, () => {
        clientSocket.pipe(targetSocket);
        targetSocket.pipe(clientSocket);
    });

    clientSocket.on('error', (err) => {
        console.error('Client socket error:', err.message);
        targetSocket.destroy();
    });

    targetSocket.on('error', (err) => {
        console.error('Target socket error:', err.message);
        clientSocket.destroy();
    });
});

server.listen(LISTEN_PORT, '0.0.0.0', () => {
    console.log(`Node Proxy listening on 0.0.0.0:${LISTEN_PORT} -> ${TARGET_HOST}:${TARGET_PORT}`);
});
