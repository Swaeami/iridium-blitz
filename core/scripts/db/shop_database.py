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
    
    def create_customer(self, telegram_id: int, telegram_username: str = None) -> Dict:
        """Create new customer"""
        customer = {
            "telegram_id": telegram_id,
            "telegram_username": telegram_username,
            "vpn_username": None,  # Set when subscription created
            "trial_used": False,
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
    
    def get_all_customers(self) -> List[Dict]:
        """Get all customers"""
        return list(self.customers.find({}))
    
    # ==================== TARIFFS ====================
    
    def create_tariff(
        self,
        name: str,
        tariff_type: str,  # "traffic" or "time"
        price: float,
        traffic_gb: Optional[int] = None,  # For traffic-based
        days: Optional[int] = None,  # For time-based
        price_stars: Optional[int] = None,  # Telegram Stars price
        is_active: bool = True
    ) -> Dict:
        """
        Create a tariff
        tariff_type: 
            - "traffic": limited traffic, unlimited time
            - "time": unlimited traffic, limited time
            - "trial": free trial (3 days, unlimited)
        """
        tariff = {
            "name": name,
            "type": tariff_type,
            "price": price,  # RUB
            "price_stars": price_stars,  # Telegram Stars
            "traffic_gb": traffic_gb,
            "days": days,
            "is_active": is_active,
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
    
    def get_active_tariffs(self, tariff_type: str = None) -> List[Dict]:
        """Get all active tariffs, optionally filtered by type"""
        query = {"is_active": True}
        if tariff_type:
            query["type"] = tariff_type
        return list(self.tariffs.find(query).sort("price", 1))
    
    def get_all_tariffs(self) -> List[Dict]:
        """Get all tariffs"""
        return list(self.tariffs.find({}).sort("created_at", -1))
    
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
        """Delete tariff (soft delete - just deactivate)"""
        return self.update_tariff(tariff_id, {"is_active": False})
    
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
        promo_type: str = "discount",  # discount, free_period, extra_traffic
        value: float = 0,  # % for discount, days for free_period, GB for extra_traffic
        max_uses: int = 1,
        tariff_ids: List[str] = None,  # Applicable tariffs (None = all)
        expires_at: datetime = None,
        description: str = ""
    ) -> Dict:
        """
        Create a promo code
        promo_type:
            - "discount": value = discount percentage (0-100)
            - "free_period": value = free days to add
            - "extra_traffic": value = extra GB to add
        """
        if not code:
            code = self.generate_promo_code()
        
        promo = {
            "code": code.upper(),
            "type": promo_type,
            "value": value,
            "max_uses": max_uses,
            "uses_count": 0,
            "tariff_ids": tariff_ids,  # None means applicable to all
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
    
    def validate_promo(self, code: str, tariff_id: str = None) -> tuple[bool, str, Optional[Dict]]:
        """
        Validate promo code
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
        
        # Check if applicable to tariff
        if tariff_id and promo.get("tariff_ids"):
            if str(tariff_id) not in [str(t) for t in promo["tariff_ids"]]:
                return False, "Промокод не применим к этому тарифу", None
        
        return True, "OK", promo
    
    def use_promo(self, code: str) -> bool:
        """Increment promo usage count"""
        result = self.promos.update_one(
            {"code": code.upper()},
            {"$inc": {"uses_count": 1}}
        )
        return result.modified_count > 0
    
    def get_all_promos(self, active_only: bool = False) -> List[Dict]:
        """Get all promo codes"""
        query = {"is_active": True} if active_only else {}
        return list(self.promos.find(query).sort("created_at", -1))
    
    def deactivate_promo(self, code: str) -> bool:
        """Deactivate promo code"""
        result = self.promos.update_one(
            {"code": code.upper()},
            {"$set": {"is_active": False}}
        )
        return result.modified_count > 0
    
    # ==================== PAYMENTS ====================
    
    def create_payment(
        self,
        customer_id: int,
        tariff_id,
        amount: float,
        payment_method: str,  # "stars", "yookassa"
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
            "external_id": None,  # YooKassa payment ID or Stars payment
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

