"""
Shop Database Models for Client Bot
Collections: customers, tariffs, promos, payments
"""

import pymongo
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import secrets
import string


class ShopDatabase:
    def __init__(self, db_name="blitz_panel"):
        try:
            self.client = pymongo.MongoClient("mongodb://localhost:27017/")
            self.db = self.client[db_name]
            
            # Collections
            self.customers = self.db["customers"]
            self.tariffs = self.db["tariffs"]
            self.promos = self.db["promos"]
            self.payments = self.db["payments"]
            
            # Ensure indexes
            self._create_indexes()
            
            self.client.server_info()
        except pymongo.errors.ConnectionFailure as e:
            print(f"Could not connect to MongoDB: {e}")
            raise
    
    def _create_indexes(self):
        """Create indexes for better query performance"""
        self.customers.create_index("telegram_id", unique=True)
        self.customers.create_index("vpn_username", sparse=True)
        self.promos.create_index("code", unique=True)
        self.payments.create_index("customer_id")
        self.payments.create_index("created_at")
    
    # ==================== CUSTOMERS ====================
    
    def get_customer(self, telegram_id: int) -> Optional[Dict]:
        """Get customer by Telegram ID"""
        return self.customers.find_one({"telegram_id": telegram_id})
    
    def get_customer_by_vpn_username(self, vpn_username: str) -> Optional[Dict]:
        """Get customer by VPN username"""
        return self.customers.find_one({"vpn_username": vpn_username.lower()})
    
    def get_customer_by_telegram_username(self, username: str) -> Optional[Dict]:
        """Get customer by Telegram username (case-insensitive)"""
        # Remove @ if present
        username = username.lstrip('@').lower()
        return self.customers.find_one({
            "telegram_username": {"$regex": f"^{username}$", "$options": "i"}
        })
    
    def create_customer(self, telegram_id: int, telegram_username: str = None) -> Dict:
        """Create new customer"""
        customer = {
            "telegram_id": telegram_id,
            "telegram_username": telegram_username,
            "vpn_username": None,  # Set when subscription created
            "trial_used": False,
            "used_promos": [],  # Track which promo codes user has used
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow()
        }
        self.customers.insert_one(customer)
        return customer
    
    def update_customer(self, telegram_id: int, updates: Dict) -> bool:
        """Update customer data"""
        updates["last_active"] = datetime.utcnow()
        result = self.customers.update_one(
            {"telegram_id": telegram_id},
            {"$set": updates}
        )
        return result.modified_count > 0
    
    def mark_trial_used(self, telegram_id: int) -> bool:
        """Mark trial as used for customer"""
        return self.update_customer(telegram_id, {"trial_used": True})
    
    def mark_promo_used(self, telegram_id: int, promo_code: str) -> bool:
        """Mark promo code as used by customer"""
        result = self.customers.update_one(
            {"telegram_id": telegram_id},
            {"$addToSet": {"used_promos": promo_code.upper()}}
        )
        return result.modified_count > 0
    
    def has_used_promo(self, telegram_id: int, promo_code: str) -> bool:
        """Check if customer has already used this promo code"""
        customer = self.get_customer(telegram_id)
        if customer:
            used_promos = customer.get("used_promos", [])
            return promo_code.upper() in used_promos
        return False
    
    def get_all_customers(self) -> List[Dict]:
        """Get all customers"""
        return list(self.customers.find({}))
    
    # ==================== TARIFFS ====================
    
    def create_tariff(
        self,
        name: str,
        days: int,  # Subscription duration in days
        price_stars: int,  # Telegram Stars price
        is_active: bool = True,
        order: int = 0  # Display order (lower = first)
    ) -> Dict:
        """
        Create a time-based tariff (unlimited traffic)
        """
        # Get max order if not specified
        if order == 0:
            max_order = self.tariffs.find_one(sort=[("order", -1)])
            order = (max_order.get("order", 0) + 1) if max_order else 1
        
        tariff = {
            "name": name,
            "days": days,
            "price_stars": price_stars,
            "is_active": is_active,
            "order": order,
            "created_at": datetime.utcnow()
        }
        result = self.tariffs.insert_one(tariff)
        tariff["_id"] = result.inserted_id
        return tariff
    
    def get_tariff(self, tariff_id) -> Optional[Dict]:
        """Get tariff by ID"""
        from bson.objectid import ObjectId
        if isinstance(tariff_id, str):
            tariff_id = ObjectId(tariff_id)
        return self.tariffs.find_one({"_id": tariff_id})
    
    def get_active_tariffs(self) -> List[Dict]:
        """Get all active tariffs sorted by order"""
        return list(self.tariffs.find({"is_active": True}).sort("order", 1))
    
    def get_all_tariffs(self) -> List[Dict]:
        """Get all tariffs sorted by order"""
        return list(self.tariffs.find({}).sort("order", 1))
    
    def update_tariff(self, tariff_id, updates: Dict) -> bool:
        """Update tariff"""
        from bson.objectid import ObjectId
        if isinstance(tariff_id, str):
            tariff_id = ObjectId(tariff_id)
        result = self.tariffs.update_one(
            {"_id": tariff_id},
            {"$set": updates}
        )
        return result.modified_count > 0
    
    def delete_tariff(self, tariff_id) -> bool:
        """Delete tariff permanently"""
        from bson.objectid import ObjectId
        if isinstance(tariff_id, str):
            tariff_id = ObjectId(tariff_id)
        result = self.tariffs.delete_one({"_id": tariff_id})
        return result.deleted_count > 0
    
    def reorder_tariff(self, tariff_id, new_order: int) -> bool:
        """Change tariff display order"""
        return self.update_tariff(tariff_id, {"order": new_order})
    
    def move_tariff_up(self, tariff_id) -> bool:
        """Move tariff up in display order"""
        from bson.objectid import ObjectId
        if isinstance(tariff_id, str):
            tariff_id = ObjectId(tariff_id)
        
        tariff = self.get_tariff(tariff_id)
        if not tariff:
            return False
        
        current_order = tariff.get("order", 0)
        
        # Find tariff with lower order (higher in list)
        prev_tariff = self.tariffs.find_one(
            {"order": {"$lt": current_order}, "is_active": True},
            sort=[("order", -1)]
        )
        
        if prev_tariff:
            # Swap orders
            self.update_tariff(tariff_id, {"order": prev_tariff["order"]})
            self.update_tariff(prev_tariff["_id"], {"order": current_order})
            return True
        return False
    
    def move_tariff_down(self, tariff_id) -> bool:
        """Move tariff down in display order"""
        from bson.objectid import ObjectId
        if isinstance(tariff_id, str):
            tariff_id = ObjectId(tariff_id)
        
        tariff = self.get_tariff(tariff_id)
        if not tariff:
            return False
        
        current_order = tariff.get("order", 0)
        
        # Find tariff with higher order (lower in list)
        next_tariff = self.tariffs.find_one(
            {"order": {"$gt": current_order}, "is_active": True},
            sort=[("order", 1)]
        )
        
        if next_tariff:
            # Swap orders
            self.update_tariff(tariff_id, {"order": next_tariff["order"]})
            self.update_tariff(next_tariff["_id"], {"order": current_order})
            return True
        return False
    
    # ==================== PROMO CODES ====================
    
    def generate_promo_code(self, length: int = 8) -> str:
        """Generate random promo code"""
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(length))
            if not self.promos.find_one({"code": code}):
                return code
    
    def create_promo(
        self,
        code: str = None,
        promo_type: str = "discount",  # discount, free_period
        value: float = 0,  # % for discount, days for free_period
        max_uses: int = 1,
        tariff_ids: List[str] = None,  # Applicable tariffs (None = all)
        for_telegram_username: str = None,  # Specific username only (None = everyone)
        expires_at: datetime = None,
        description: str = ""
    ) -> Dict:
        """
        Create a promo code
        promo_type:
            - "discount": value = discount percentage (0-100)
            - "free_period": value = free days to add
        for_telegram_username: if set, only this username can use the promo
        """
        if not code:
            code = self.generate_promo_code()
        
        # Normalize username (remove @, lowercase)
        if for_telegram_username:
            for_telegram_username = for_telegram_username.lstrip('@').lower()
        
        promo = {
            "code": code.upper(),
            "type": promo_type,
            "value": value,
            "max_uses": max_uses,
            "uses_count": 0,
            "used_by": [],  # Track telegram IDs who used this code
            "tariff_ids": tariff_ids,  # None means applicable to all
            "for_telegram_username": for_telegram_username,  # If set, only this username can use
            "expires_at": expires_at,
            "description": description,
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        self.promos.insert_one(promo)
        return promo
    
    def get_promo(self, code: str) -> Optional[Dict]:
        """Get promo by code"""
        return self.promos.find_one({"code": code.upper()})
    
    def validate_promo(self, code: str, telegram_id: int = None, telegram_username: str = None, tariff_id: str = None) -> tuple[bool, str, Optional[Dict]]:
        """
        Validate promo code for a specific user
        Returns: (is_valid, message, promo_data)
        """
        promo = self.get_promo(code)
        
        if not promo:
            return False, "Промокод не найден", None
        
        if not promo.get("is_active", True):
            return False, "Промокод неактивен", None
        
        if promo.get("expires_at") and promo["expires_at"] < datetime.utcnow():
            return False, "Промокод истёк", None
        
        if promo["uses_count"] >= promo["max_uses"]:
            return False, "Промокод исчерпан", None
        
        # Check if promo is for specific username
        if promo.get("for_telegram_username"):
            if not telegram_username:
                return False, "Промокод недоступен для вас", None
            # Normalize and compare usernames (case-insensitive)
            promo_username = promo["for_telegram_username"].lower()
            user_username = telegram_username.lstrip('@').lower()
            if promo_username != user_username:
                return False, "Промокод недоступен для вас", None
        
        # Check if user already used this promo
        if telegram_id:
            used_by = promo.get("used_by", [])
            if telegram_id in used_by:
                return False, "Вы уже использовали этот промокод", None
        
        # Check if applicable to tariff
        if tariff_id and promo.get("tariff_ids"):
            if str(tariff_id) not in [str(t) for t in promo["tariff_ids"]]:
                return False, "Промокод не применим к этому тарифу", None
        
        return True, "OK", promo
    
    def use_promo(self, code: str, telegram_id: int) -> bool:
        """Mark promo as used by user"""
        result = self.promos.update_one(
            {"code": code.upper()},
            {
                "$inc": {"uses_count": 1},
                "$addToSet": {"used_by": telegram_id}
            }
        )
        # Also track in customer record
        self.mark_promo_used(telegram_id, code)
        return result.modified_count > 0
    
    def get_all_promos(self, active_only: bool = False) -> List[Dict]:
        """Get all promo codes"""
        query = {"is_active": True} if active_only else {}
        return list(self.promos.find(query).sort("created_at", -1))
    
    def get_promos_for_username(self, username: str) -> List[Dict]:
        """Get available promo codes assigned to a specific username"""
        if not username:
            return []
        username = username.lstrip('@').lower()
        return list(self.promos.find({
            "for_telegram_username": username,
            "is_active": True,
            "$expr": {"$lt": ["$uses_count", "$max_uses"]}
        }))
    
    def delete_promo(self, code: str) -> bool:
        """Delete promo code permanently"""
        result = self.promos.delete_one({"code": code.upper()})
        return result.deleted_count > 0
    
    # ==================== PAYMENTS ====================
    
    def create_payment(
        self,
        customer_id: int,
        tariff_id,
        amount: float,
        payment_method: str = "stars",
        promo_code: str = None
    ) -> Dict:
        """Create payment record"""
        from bson.objectid import ObjectId
        
        payment = {
            "customer_id": customer_id,
            "tariff_id": ObjectId(tariff_id) if isinstance(tariff_id, str) else tariff_id,
            "amount": amount,
            "payment_method": payment_method,
            "promo_code": promo_code,
            "status": "pending",  # pending, completed, failed, refunded
            "external_id": None,  # Stars payment ID
            "created_at": datetime.utcnow(),
            "completed_at": None
        }
        result = self.payments.insert_one(payment)
        payment["_id"] = result.inserted_id
        return payment
    
    def get_payment(self, payment_id) -> Optional[Dict]:
        """Get payment by ID"""
        from bson.objectid import ObjectId
        if isinstance(payment_id, str):
            payment_id = ObjectId(payment_id)
        return self.payments.find_one({"_id": payment_id})
    
    def update_payment(self, payment_id, updates: Dict) -> bool:
        """Update payment"""
        from bson.objectid import ObjectId
        if isinstance(payment_id, str):
            payment_id = ObjectId(payment_id)
        result = self.payments.update_one(
            {"_id": payment_id},
            {"$set": updates}
        )
        return result.modified_count > 0
    
    def complete_payment(self, payment_id, external_id: str = None) -> bool:
        """Mark payment as completed"""
        return self.update_payment(payment_id, {
            "status": "completed",
            "external_id": external_id,
            "completed_at": datetime.utcnow()
        })
    
    def get_customer_payments(self, customer_id: int) -> List[Dict]:
        """Get all payments for customer"""
        return list(self.payments.find({"customer_id": customer_id}).sort("created_at", -1))
    
    def get_payments_stats(self, days: int = 30) -> Dict:
        """Get payment statistics for last N days"""
        since = datetime.utcnow() - timedelta(days=days)
        pipeline = [
            {"$match": {"created_at": {"$gte": since}, "status": "completed"}},
            {"$group": {
                "_id": "$payment_method",
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1}
            }}
        ]
        results = list(self.payments.aggregate(pipeline))
        return {r["_id"]: {"total": r["total"], "count": r["count"]} for r in results}


# Singleton instance
try:
    shop_db = ShopDatabase()
except pymongo.errors.ConnectionFailure:
    shop_db = None
