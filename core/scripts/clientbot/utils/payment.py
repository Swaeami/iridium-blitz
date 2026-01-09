"""
Payment utilities for Client Bot
Supports: Telegram Stars
"""

from typing import Dict, Tuple


class PaymentManager:
    def __init__(self, *args, **kwargs):
        """Initialize payment manager for Telegram Stars only"""
        pass
    
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
