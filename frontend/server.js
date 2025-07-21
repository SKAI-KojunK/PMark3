const express = require('express');
const path = require('path');
const net = require('net');
const http = require('http');

const app = express();

// 포트 사용 가능 여부 확인 함수
function checkPortAvailable(port) {
    return new Promise((resolve) => {
        const server = net.createServer();
        server.listen(port, () => {
            server.once('close', () => {
                resolve(true);
            });
            server.close();
        });
        server.on('error', () => {
            resolve(false);
        });
    });
}

// 사용 가능한 포트 찾기 함수
async function findFreePort(startPort = 3010, maxAttempts = 20) {
    for (let port = startPort; port < startPort + maxAttempts; port++) {
        // PMark2와 충돌 방지 (3000-3009 건너뛰기)
        if (port >= 3000 && port <= 3009) {
            continue;
        }
        
        if (await checkPortAvailable(port)) {
            return port;
        }
    }
    return null;
}

// 백엔드 포트 찾기 함수
async function findBackendPort(startPort = 8010, maxAttempts = 20) {
    for (let port = startPort; port < startPort + maxAttempts; port++) {
        // PMark2와 충돌 방지 (8000-8009 건너뛰기)
        if (port >= 8000 && port <= 8009) {
            continue;
        }
        
        try {
            const isAlive = await checkBackendHealth(port);
            if (isAlive) {
                return port;
            }
        } catch (e) {
            // 포트에 서버가 없음
        }
    }
    return null;
}

// 백엔드 헬스 체크 함수
function checkBackendHealth(port) {
    return new Promise((resolve) => {
        const req = http.get(`http://localhost:${port}/health`, (res) => {
            resolve(res.statusCode === 200);
        });
        
        req.on('error', () => {
            resolve(false);
        });
        
        req.setTimeout(1000, () => {
            req.destroy();
            resolve(false);
        });
    });
}

// 메인 시작 함수
async function startServer() {
    console.log('🚀 PMark2.5 Frontend Server 시작 중...');
    
    // 사용 가능한 프론트엔드 포트 찾기
    const PORT = process.env.TEST_FRONTEND_PORT || await findFreePort(3010);
    
    if (!PORT) {
        console.error('❌ 사용 가능한 프론트엔드 포트를 찾을 수 없습니다.');
        process.exit(1);
    }
    
    // 백엔드 포트 찾기
    const backendPort = await findBackendPort(8010);
    
    if (!backendPort) {
        console.warn('⚠️ 백엔드 서버를 찾을 수 없습니다. 기본값(8010)을 사용합니다.');
    }
    
    // 정적 파일 제공
    app.use(express.static(path.join(__dirname, '..')));

    // 메인 페이지
    app.get('/', (req, res) => {
        res.sendFile(path.join(__dirname, '..', 'test_chatbot.html'));
    });

    // 헬스 체크
    app.get('/health', (req, res) => {
        res.json({ 
            status: 'healthy', 
            port: PORT,
            backendPort: backendPort || 8010
        });
    });

    // 백엔드 포트 정보 제공 API
    app.get('/api/backend-info', (req, res) => {
        res.json({
            backendPort: backendPort || 8010,
            backendUrl: `http://localhost:${backendPort || 8010}/api/v1`
        });
    });

    app.listen(PORT, () => {
        console.log(`🚀 PMark2.5 Frontend Server running on port ${PORT}`);
        console.log(`📱 Access: http://localhost:${PORT}`);
        if (backendPort) {
            console.log(`🔗 Backend connected: http://localhost:${backendPort}`);
        } else {
            console.log(`⚠️ Backend not found - using default: http://localhost:8010`);
        }
    });
}

// 서버 시작
startServer().catch(console.error); 