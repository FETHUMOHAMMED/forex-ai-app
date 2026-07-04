require('dotenv').config({ path: '../.env' });
const express = require('express');
const cors = require('cors');
const WebSocket = require('ws');
const { spawn } = require('child_process');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();

const app = express();
const PORT = process.env.PORT || 3001;
const WS_PORT = process.env.WS_PORT || 8080;

// Configuration (from .env or defaults)
const STARTING_BALANCE = parseFloat(process.env.STARTING_BALANCE) || 500000;
const MIN_TRADING_DAYS_FOR_SHARPE = parseInt(process.env.MIN_DAYS_SHARPE) || 30;
const SIGNAL_REFRESH_INTERVAL = parseInt(process.env.SIGNAL_REFRESH_MS) || 15000;
const MAX_CONSECUTIVE_ERRORS = parseInt(process.env.MAX_CONSEC_ERRORS) || 2;

app.use(cors({ origin: 'http://localhost:3000' }));
app.use(express.json());
app.use('/api', (req, res, next) => {
    const key = req.headers['x-api-key'];
    if (key !== process.env.API_KEY) {
        return res.status(401).json({ error: 'Unauthorized' });
    }
    next();
});

// State tracking
let latestSignals = [];
let lastUpdateTime = null;
let lastUpdateStatus = 'pending';
let consecutiveErrors = 0;
let isUpdating = false;
let lastSignalVersion = -1;
// Health check
app.get('/health', (req, res) => res.json({ 
    status: 'ok',
    lastUpdate: lastUpdateTime,
    updateStatus: lastUpdateStatus,
    signalCount: latestSignals.length,
    consecutiveErrors: consecutiveErrors,
    uptime: process.uptime()
}));

// Get latest signals
app.get('/api/signals', (req, res) => res.json(latestSignals));

// --- Fixed Stats endpoint ---
app.get('/api/stats', (req, res) => {
    const dbPath = path.join(__dirname, '../ai-service/trades.db');
    const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READONLY, (err) => {
        if (err) {
            console.error('Could not open database:', err.message);
            return res.json({ error: 'Database not available' });
        }
    });

    const stats = {
        total_trades: 0,
        winning_trades: 0,
        losing_trades: 0,
        win_rate: 0,
        total_pnl: 0,
        avg_confidence: 0,
        best_trade: 0,
        worst_trade: 0,
        open_positions: 0,
        today_pnl: 0,
        sharpe_ratio: null,
        rolling_win_rate: 0,
        max_drawdown: 0,
        profit_factor: null,
        starting_balance: STARTING_BALANCE
    };

    // Get all closed trades for calculations
    db.all(`
        SELECT pnl, confidence, result, timestamp 
        FROM trades 
        WHERE exit_price IS NOT NULL AND pnl IS NOT NULL
        ORDER BY timestamp ASC
    `, (err, rows) => {
        if (err) {
            console.error('Query error:', err.message);
            db.close();
            return res.json(stats);
        }

        if (rows && rows.length > 0) {
            const totalTrades = rows.length;
            const wins = rows.filter(r => r.pnl > 0).length;
            const losses = rows.filter(r => r.pnl < 0).length;

            stats.total_trades = totalTrades;
            stats.winning_trades = wins;
            stats.losing_trades = losses;
            stats.win_rate = totalTrades > 0 ? (wins / totalTrades) * 100 : 0;

            const pnlValues = rows.map(r => r.pnl);
            stats.total_pnl = pnlValues.reduce((a, b) => a + b, 0);
            stats.best_trade = Math.max(...pnlValues);
            stats.worst_trade = Math.min(...pnlValues);
            stats.avg_confidence = rows.reduce((a, r) => a + (r.confidence || 0), 0) / totalTrades;

            // Rolling win rate (last 20 trades)
            const last20 = rows.slice(-20);
            const rollingWins = last20.filter(r => r.pnl > 0).length;
            stats.rolling_win_rate = last20.length > 0 ? (rollingWins / last20.length) * 100 : 0;

            // Profit Factor - safe, no Infinity
            const grossProfit = rows.filter(r => r.pnl > 0).reduce((a, r) => a + r.pnl, 0);
            const grossLoss = Math.abs(rows.filter(r => r.pnl < 0).reduce((a, r) => a + r.pnl, 0));
            
            if (grossLoss > 0) {
                stats.profit_factor = grossProfit / grossLoss;
            } else if (grossProfit > 0) {
                stats.profit_factor = 999;
            } else {
                stats.profit_factor = null;
            }

            // Max Drawdown calculation with starting balance
            let balance = STARTING_BALANCE;
            let peak = STARTING_BALANCE;
            let maxDrawdown = 0;

            for (const r of rows) {
                balance += r.pnl;
                if (balance > peak) {
                    peak = balance;
                }
                const drawdown = ((balance - peak) / peak) * 100;
                if (drawdown < maxDrawdown) {
                    maxDrawdown = drawdown;
                }
            }
            stats.max_drawdown = Math.max(maxDrawdown, -100);

            // Sharpe Ratio with sample variance (n-1)
            const dailyPnL = {};
            for (const r of rows) {
                const day = r.timestamp.slice(0, 10);
                if (!dailyPnL[day]) dailyPnL[day] = 0;
                dailyPnL[day] += r.pnl;
            }
            const dailyReturns = Object.values(dailyPnL);

            if (dailyReturns.length >= MIN_TRADING_DAYS_FOR_SHARPE && dailyReturns.length > 1) {
                const dailyPctReturns = dailyReturns.map(p => p / STARTING_BALANCE);
                const avgDailyReturn = dailyPctReturns.reduce((a, b) => a + b, 0) / dailyPctReturns.length;
                
                const squaredDiffs = dailyPctReturns.reduce((a, b) => a + Math.pow(b - avgDailyReturn, 2), 0);
                const variance = squaredDiffs / (dailyPctReturns.length - 1);
                const stdDaily = Math.sqrt(variance);
                
                const annualizedReturn = avgDailyReturn * 252;
                const annualizedStd = stdDaily * Math.sqrt(252);
                stats.sharpe_ratio = annualizedStd !== 0 ? annualizedReturn / annualizedStd : 0;
            } else {
                stats.sharpe_ratio = null;
            }
        }

        // Count open positions
        db.get(`SELECT COUNT(*) as open_positions FROM trades WHERE exit_price IS NULL`, (err2, row2) => {
            if (!err2 && row2) {
                stats.open_positions = row2.open_positions || 0;
            }

            // Get today's P&L
            const today = new Date().toISOString().split('T')[0];
            db.get(`SELECT SUM(pnl) as today_pnl FROM trades WHERE date(timestamp) = ?`, [today], (err3, row3) => {
                if (!err3 && row3) {
                    stats.today_pnl = row3.today_pnl || 0;
                }
                db.close();
                res.json(stats);
            });
        });
    });
});

// --- Fixed Equity Curve endpoint ---
app.get('/api/equity-curve', (req, res) => {
    const dbPath = path.join(__dirname, '../ai-service/trades.db');
    const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READONLY, (err) => {
        if (err) {
            console.error('Could not open database:', err.message);
            return res.json([]);
        }
    });

    db.all(`
        SELECT timestamp, pnl 
        FROM trades 
        WHERE exit_price IS NOT NULL AND pnl IS NOT NULL
        ORDER BY timestamp ASC
    `, (err, rows) => {
        if (err) {
            console.error('Query error:', err.message);
            db.close();
            return res.json([]);
        }

        const equityData = [];
        let cumulative = STARTING_BALANCE;

        const dailyMap = {};
        for (const row of rows) {
            const day = row.timestamp.slice(0, 10);
            if (!dailyMap[day]) dailyMap[day] = 0;
            dailyMap[day] += row.pnl;
        }

        const sortedDays = Object.keys(dailyMap).sort();
        for (const day of sortedDays) {
            cumulative += dailyMap[day];
            equityData.push({
                date: day,
                balance: parseFloat(cumulative.toFixed(2))
            });
        }

        if (equityData.length === 0) {
            const today = new Date().toISOString().split('T')[0];
            equityData.push({
                date: today,
                balance: STARTING_BALANCE
            });
        }

        db.close();
        res.json(equityData);
    });
});

// --- AI Signals Function ---
// --- AI Signals Function (Uses long-running FastAPI service) ---
// --- AI Signals Function (Uses long-running FastAPI service) ---
// --- AI Signals Function (Uses long-running FastAPI service) ---
function getAISignals() {
    return new Promise((resolve, reject) => {
        const http = require('http');
        const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8001/signals';
        
        const timeout = setTimeout(() => {
            reject(new Error('AI service timeout'));
        }, 5000); // Fast - no Python spawning needed
        
        http.get(AI_SERVICE_URL, (res) => {
            let data = '';
            
            res.on('data', (chunk) => {
                data += chunk;
            });
            
            res.on('end', () => {
                clearTimeout(timeout);
                
                try {
                    const response = JSON.parse(data);
                    resolve(response.signals || []);
                } catch (e) {
                    console.error('❌ Failed to parse AI service response:', e.message);
                    reject(new Error('Invalid response'));
                }
            });
        }).on('error', (err) => {
            clearTimeout(timeout);
            console.error('❌ AI service connection failed:', err.message);
            reject(new Error(`Cannot connect to AI service: ${err.message}`));
        });
    });
}

// --- WebSocket Server ---
const wss = new WebSocket.Server({ port: WS_PORT });

wss.on('connection', (ws) => {
    console.log(`🔌 Client connected (total: ${wss.clients.size})`);
    
    ws.send(JSON.stringify({ 
        type: 'connected', 
        timestamp: new Date().toISOString(),
        signalCount: latestSignals.length
    }));
    
    if (latestSignals.length > 0) {
        ws.send(JSON.stringify({ 
            type: 'signals', 
            data: latestSignals, 
            timestamp: new Date().toISOString() 
        }));
    }

    ws.on('close', () => {
        console.log(`🔌 Client disconnected (remaining: ${wss.clients.size})`);
    });

    ws.on('error', (err) => {
        console.error('WebSocket error:', err.message);
    });
});

function broadcast(signals) {
    const message = JSON.stringify({ 
        type: 'signals', 
        data: signals, 
        timestamp: new Date().toISOString(),
        count: signals.length
    });
    
    let sentCount = 0;
    wss.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(message);
            sentCount++;
        }
    });
    
    return sentCount;
}

// --- Signal Update Loop ---

// Find the update() function and replace with:
async function update() {
    if (isUpdating) {
        console.log('⏳ Update already in progress, skipping...');
        return;
    }
    
    isUpdating = true;
    
    try {
        const http = require('http');
        const AI_SERVICE_URL = 'http://localhost:8001/signals';
        
        const response = await new Promise((resolve, reject) => {
            http.get(AI_SERVICE_URL, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try { resolve(JSON.parse(data)); }
                    catch(e) { reject(e); }
                });
            }).on('error', reject);
        });
        
        const newVersion = response.version || 0;
        
        // Only broadcast if version changed
        if (newVersion !== lastSignalVersion) {
            lastSignalVersion = newVersion;
            latestSignals = response.signals || [];
            const clientCount = broadcast(latestSignals);
            lastUpdateTime = new Date().toISOString();
            
            if (latestSignals.length > 0) {
                lastUpdateStatus = 'success';
                console.log(`✅ Broadcast v${newVersion}: ${latestSignals.length} signals to ${clientCount} clients`);
            } else {
                lastUpdateStatus = 'empty';
                console.log(`📭 v${newVersion}: No trade setups (market scanned successfully)`);
            }
        }
        
        consecutiveErrors = 0;
        
    } catch (error) {
        consecutiveErrors++;
        console.error(`❌ Signal update failed (#${consecutiveErrors}): ${error.message}`);
        lastUpdateStatus = 'error';
        
        if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
            console.warn(`⚠️ ${consecutiveErrors} consecutive errors - clearing stale signals`);
            latestSignals = [];
            broadcast([]);
        }
    } finally {
        isUpdating = false;
    }
}

// --- Start Server ---
app.listen(PORT, () => {
    console.log('═'.repeat(50));
    console.log(`🚀 Forex AI Backend Running`);
    console.log(`   HTTP:      http://localhost:${PORT}`);
    console.log(`   WebSocket: ws://localhost:${WS_PORT}`);
    console.log(`   Balance:   $${STARTING_BALANCE.toLocaleString()}`);
    console.log(`   Refresh:   ${SIGNAL_REFRESH_INTERVAL / 1000}s`);
    console.log(`   Max Errors: ${MAX_CONSECUTIVE_ERRORS} before clearing`);
    console.log('═'.repeat(50));
    
    update();
    setInterval(update, SIGNAL_REFRESH_INTERVAL);
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\n🛑 Shutting down gracefully...');
    wss.close();
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\n🛑 Received SIGTERM - shutting down...');
    wss.close();
    process.exit(0);
});