require('dotenv').config();
const express = require('express');
const cors    = require('cors');
const { initDB, pool } = require('./config/database');

const app = express();
app.use(cors());
app.use(express.json());

// ── Routes ───────────────────────────────────────────────────────────────────
app.use('/api/news',      require('./routes/news'));
app.use('/api/auth',      require('./routes/auth'));
app.use('/api/watchlist', require('./routes/watchlist'));
app.use('/api/search',    require('./routes/search'));
app.use('/api/price',     require('./routes/price')); 

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', time: new Date().toISOString() });
});

app.get('/', (req, res) => {
  res.json({ success: true, message: 'Gramble API running' });
});

// ── AUTO DELETE ARTICLES OLDER THAN 7 DAYS ──────────────────────────────────
async function deleteOldArticles() {
  try {
    const result = await pool.query(
      `DELETE FROM articles WHERE published_at < NOW() - INTERVAL '7 days'`
    );
    console.log(`🗑️ Deleted ${result.rowCount} articles older than 7 days`);
  } catch (err) {
    console.error('Auto-delete error:', err.message);
  }
}

initDB().then(async () => {
  await deleteOldArticles();
  setInterval(deleteOldArticles, 24 * 60 * 60 * 1000);

  const PORT = process.env.PORT || 5000;
  app.listen(PORT, () => console.log(`✅ Server running on port ${PORT}`));
}).catch(err => {
  console.error('DB init failed:', err.message);
  process.exit(1);
});