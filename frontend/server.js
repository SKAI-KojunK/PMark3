const express = require('express');
const path = require('path');
const app = express();
const port = process.env.PORT || 3001;

// 정적 파일 제공
app.use(express.static(path.join(__dirname, '..')));

// 모든 요청에 대해 chatbot.html 반환
app.get('*', function(req, res) {
  res.sendFile(path.join(__dirname, '..', 'chatbot.html'));
});

app.listen(port, function() {
  console.log(`Frontend server is running on port ${port}`);
  console.log(`Open http://localhost:${port} in your browser`);
}); 