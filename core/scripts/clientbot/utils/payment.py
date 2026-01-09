"""
Payment utilities for Client Bot
Supports: Telegram Stars, YooKassa
"""

import os
import uuid
import json
from typing import Optional, Dict, Tuple
from datetime import datetime

# YooKassa SDK
try:
    from yookassa import Configuration, Payment
    YOOKASSA_AVAILABLE = True
except ImportError:
    YOOKASSA_AVAILABLE = False


class PaymentManager:
    def __init__(self, yookassa_shop_id: str = None, yookassa_secret_key: str = None):
        self.yookassa_shop_id = yookassa_shop_id
        self.yookassa_secret_key = yookassa_secret_key
        
        # Configure YooKassa if credentials provided
        if YOOKASSA_AVAILABLE and yookassa_shop_id and yookassa_secret_key:
            Configuration.account_id = yookassa_shop_id
            Configuration.secret_key = yookassa_secret_key
            self.yookassa_enabled = True
        else:
            self.yookassa_enabled = False
    
    # ==================== TELEGRAM STARS ====================
    
    def create_stars_invoice(
        self,
        bot,
        chat_id: int,
        title: str,
        description: str,
        payload: str,
        amount: int,  # Stars amount
        photo_url: str = None
    ) -> bool:
        """
        Create Telegram Stars invoice
        Returns: True if invoice sent successfully
        """
        try:
            prices = [{"label": title, "amount": amount}]
            
            bot.send_invoice(
                chat_id=chat_id,
                title=title,
                description=description,
                invoice_payload=payload,
                provider_token="",  # Empty for Stars
                currency="XTR",  # Telegram Stars currency
                prices=prices,
                photo_url=photo_url,
                photo_width=512,
                photo_height=512,
                need_name=False,
                need_email=False,
                need_phone_number=False,
                is_flexible=False,
                start_parameter=payload
            )
            return True
        except Exception as e:
            print(f"Error creating Stars invoice: {e}")
            return False
    
    def process_stars_payment(self, pre_checkout_query) -> Tuple[bool, str]:
        """
        Process Stars pre-checkout query
        Returns: (success, message)
        """
        # Stars payments are always valid if they reach pre_checkout
        return True, "OK"
    
    def confirm_stars_payment(self, successful_payment) -> Dict:
        """
        Extract payment info from successful Stars payment
        Returns payment details dict
        """
        return {
            "payment_id": successful_payment.telegram_payment_charge_id,
            "provider_payment_id": successful_payment.provider_payment_charge_id,
            "amount": successful_payment.total_amount,
            "currency": successful_payment.currency,
            "payload": successful_payment.invoice_payload
        }
    
    # ==================== YOOKASSA ====================
    
    def create_yookassa_payment(
        self,
        amount: float,
        description: str,
        return_url: str,
        metadata: Dict = None
    ) -> Optional[Dict]:
        """
        Create YooKassa payment
        Returns: payment data with confirmation_url or None
        """
        if not self.yookassa_enabled:
            print("YooKassa not configured")
            return None
        
        try:
            idempotence_key = str(uuid.uuid4())
            
            payment = Payment.create({
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url
                },
                "capture": True,
                "description": description,
                "metadata": metadata or {}
            }, idempotence_key)
            
            return {
                "payment_id": payment.id,
                "status": payment.status,
                "confirmation_url": payment.confirmation.confirmation_url,
                "amount": float(payment.amount.value),
                "created_at": payment.created_at
            }
        except Exception as e:
            print(f"Error creating YooKassa payment: {e}")
            return None
    
    def check_yookassa_payment(self, payment_id: str) -> Optional[Dict]:
        """
        Check YooKassa payment status
        Returns: payment status dict or None
        """
        if not self.yookassa_enabled:
            return None
        
        try:
            payment = Payment.find_one(payment_id)
            return {
                "payment_id": payment.id,
                "status": payment.status,  # pending, waiting_for_capture, succeeded, canceled
                "paid": payment.paid,
                "amount": float(payment.amount.value),
                "metadata": payment.metadata
            }
        except Exception as e:
            print(f"Error checking YooKassa payment: {e}")
            return None
    
    def is_payment_successful(self, payment_id: str) -> bool:
        """Check if YooKassa payment succeeded"""
        status = self.check_yookassa_payment(payment_id)
        return status and status.get("status") == "succeeded"


# Webhook handler for YooKassa notifications
def parse_yookassa_webhook(data: Dict) -> Optional[Dict]:
    """
    Parse YooKassa webhook notification
    Returns: parsed event data or None
    """
    try:
        event_type = data.get("event")
        payment_obj = data.get("object", {})
        
        if event_type == "payment.succeeded":
            return {
                "event": "payment_success",
                "payment_id": payment_obj.get("id"),
                "amount": float(payment_obj.get("amount", {}).get("value", 0)),
                "metadata": payment_obj.get("metadata", {})
            }
        elif event_type == "payment.canceled":
            return {
                "event": "payment_canceled",
                "payment_id": payment_obj.get("id"),
                "reason": payment_obj.get("cancellation_details", {}).get("reason")
            }
        
        return None
    except Exception as e:
        print(f"Error parsing YooKassa webhook: {e}")
        return None

