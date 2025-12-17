import time
import hmac
import hashlib
import requests
import json
import urllib.parse
import pandas as pd
from datetime import datetime

class DeltaExchange:
    def __init__(self, api_key, api_secret, base_url="https://api.india.delta.exchange"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url

    def _generate_signature(self, method, path, payload, timestamp):
        """
        Generates the HMAC SHA256 signature for the request.
        """
        if method == "GET" and payload:
             path = path + "?" + urllib.parse.urlencode(payload)
             body_str = ""
        else:
            body_str = json.dumps(payload) if payload else ""
            
        signature_data = method + timestamp + path + body_str
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _request(self, method, endpoint, payload=None, auth=True):
        url = self.base_url + endpoint
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'python-bot'
        }
        
        if auth:
            timestamp = str(int(time.time()))
            signature = self._generate_signature(method, endpoint, payload, timestamp)
            headers.update({
                'api-key': self.api_key,
                'signature': signature,
                'timestamp': timestamp
            })

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=payload)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=payload)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, json=payload)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            if response.text:
                print(f"Response Body: {response.text}")
            return None
        except Exception as e:
            print(f"Request Error: {e}")
            return None

    def get_product_id(self, symbol):
        # NOTE: Cached id lookup would be better for performance, doing it simple for now
        data = self._request("GET", "/v2/products", auth=False)
        if data and data.get("success"):
            for product in data["result"]:
                if product["symbol"] == symbol:
                    return product["id"]
        return None

    def fetch_candles(self, symbol, timeframe="15m", start=None, end=None):
        """
        Fetches candles and returns a Pandas DataFrame.
        """
        if end is None:
            end = int(time.time())
        if start is None:
            start = end - (24 * 60 * 60) # Default last 24h
            
        params = {
            "resolution": timeframe,
            "symbol": symbol,
            "start": start,
            "end": end
        }
        
        data = self._request("GET", "/v2/history/candles", params, auth=False)
        if data and data.get("success") and data.get("result"):
            candles = data["result"]
            # Convert to DataFrame
            df = pd.DataFrame(candles)
            # Ensure columns are float/int
            df['close'] = df['close'].astype(float)
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['volume'] = df['volume'].astype(float)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            # Sort by time ascending
            df = df.sort_values('time').reset_index(drop=True)
            return df
        return pd.DataFrame() # Empty DF if failed

    def place_order(self, product_id, size, side, order_type="limit_order", limit_price=None, stop_price=None, trail_amount=None):
        payload = {
            "product_id": product_id,
            "size": size,
            "side": side,
            "order_type": order_type,
            "time_in_force": "gtc"
        }
        
        if limit_price:
            payload["limit_price"] = str(limit_price)
        
        if stop_price:
             payload["stop_price"] = str(stop_price)
             
        if trail_amount:
            payload["trail_amount"] = str(trail_amount)

        return self._request("POST", "/v2/orders", payload, auth=True)

    def cancel_all_orders(self, product_id):
        payload = {
            "product_id": product_id
        }
        return self._request("DELETE", "/v2/orders", payload, auth=True) 
        
    def get_position(self, product_id):
        # /v2/positions
        # Returns list of positions
        data = self._request("GET", "/v2/positions", auth=True)
        if data and data.get("success"):
            for pos in data["result"]:
                if pos["product_id"] == int(product_id):
                    return pos
        return None
