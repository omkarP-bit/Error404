import { createClient } from '@supabase/supabase-js';
import { HttpsProxyAgent } from 'https-proxy-agent';
import dotenv from 'dotenv';

dotenv.config();

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseAnonKey = process.env.SUPABASE_ANON_KEY;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY;

const options = {};
if (process.env.HTTPS_PROXY) {
  options.global = {
    fetch: (url, init) => {
      return fetch(url, {
        ...init,
        agent: new HttpsProxyAgent(process.env.HTTPS_PROXY)
      });
    }
  };
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey, options);
export const supabaseAdmin = createClient(supabaseUrl, supabaseServiceKey, options);
