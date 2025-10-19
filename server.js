// Express server with security middlewares and contact endpoint
const express = require('express');
const path = require('path');
const helmet = require('helmet');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000;

// Security & logging
app.use(helmet({ contentSecurityPolicy: false }));
app.use(cors({ origin: true }));
app.use(morgan('dev'));

// Body parsers
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// Basic rate limiter for API routes
const apiLimiter = rateLimit({ windowMs: 60 * 1000, max: 30 });
app.use('/api/', apiLimiter);

// Serve static files
app.use(express.static(path.join(__dirname, 'public'), { maxAge: '6h', extensions: ['html'] }));

// Contact endpoint
app.post('/api/contact', (req, res) => {
  const { name, email, message } = req.body || {};
  if (!name || !email || !message) {
    return res.status(400).json({ ok: false, message: 'Missing fields' });
  }
  // TODO: Integrate email service or DB here
  console.log('Contact message:', { name, email, message });
  return res.json({ ok: true, message: 'Thanks — message received' });
});

// Fallback to index.html for client-side navigation (optional)
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`));
