import dotenv from 'dotenv';
dotenv.config();

import app from './src/app.js';
import config from './src/config/env.js';

const PORT = config.port;

app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`📊 Environment: ${config.nodeEnv}`);
  console.log(`🤖 ML Service: ${config.mlServiceUrl}`);
});
