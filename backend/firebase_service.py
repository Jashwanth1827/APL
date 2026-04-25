import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

class FirebaseService:
    """Firebase/Firestore integration for data persistence"""
    
    def __init__(self):
        """Initialize Firebase connection"""
        self.initialized = False
        self.db = None
        
        try:
            import firebase_admin
            from firebase_admin import credentials
            from firebase_admin import firestore
            
            # Try to initialize with credentials
            creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "./credentials/firebase-key.json")
            
            if os.path.exists(creds_path):
                cred = credentials.Certificate(creds_path)
                firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                self.initialized = True
                print("Firebase initialized successfully")
            else:
                print(f"WARNING: Firebase credentials not found at {creds_path}")
                print("Using mock Firebase mode")
        except Exception as e:
            print(f"WARNING: Could not initialize Firebase: {e}")
            print("Using mock Firebase mode")
            self._init_mock_db()
    
    def _init_mock_db(self):
        """Initialize mock database for development"""
        self.mock_db = {
            "users": {},
            "health_logs": {},
            "interventions": {},
            "user_history": {}
        }
    
    # ============ USER OPERATIONS ============
    
    def create_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Create new user profile"""
        try:
            user_data["created_at"] = datetime.now().isoformat()
            user_data["updated_at"] = datetime.now().isoformat()
            
            if self.initialized:
                self.db.collection("users").document(user_id).set(user_data)
            else:
                self.mock_db["users"][user_id] = user_data
            
            return True
        except Exception as e:
            print(f"ERROR creating user: {e}")
            return False
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user profile"""
        try:
            if self.initialized:
                doc = self.db.collection("users").document(user_id).get()
                return doc.to_dict() if doc.exists else None
            else:
                return self.mock_db["users"].get(user_id)
        except Exception as e:
            print(f"ERROR getting user: {e}")
            return None
    
    def update_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Update user profile"""
        try:
            user_data["updated_at"] = datetime.now().isoformat()
            
            if self.initialized:
                self.db.collection("users").document(user_id).update(user_data)
            else:
                if user_id in self.mock_db["users"]:
                    self.mock_db["users"][user_id].update(user_data)
            
            return True
        except Exception as e:
            print(f"ERROR updating user: {e}")
            return False
    
    # ============ HEALTH LOG OPERATIONS ============
    
    def log_health_data(self, user_id: str, health_data: Dict[str, Any]) -> str:
        """Store health data point"""
        try:
            log_entry = {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "data": health_data
            }
            
            if self.initialized:
                doc_ref = self.db.collection("health_logs").add(log_entry)
                return doc_ref[1].id
            else:
                log_id = f"log_{len(self.mock_db['health_logs'])}"
                self.mock_db["health_logs"][log_id] = log_entry
                return log_id
        except Exception as e:
            print(f"ERROR logging health data: {e}")
            return ""
    
    def get_health_logs(self, user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Retrieve recent health logs for user"""
        try:
            if self.initialized:
                docs = self.db.collection("health_logs")\
                    .where("user_id", "==", user_id)\
                    .order_by("timestamp", direction="DESCENDING")\
                    .limit(limit)\
                    .stream()
                return [doc.to_dict() for doc in docs]
            else:
                user_logs = [log for log in self.mock_db["health_logs"].values() 
                            if log.get("user_id") == user_id]
                return sorted(user_logs, key=lambda x: x["timestamp"], reverse=True)[:limit]
        except Exception as e:
            print(f"ERROR getting health logs: {e}")
            return []
    
    # ============ INTERVENTION OPERATIONS ============
    
    def log_intervention(self, user_id: str, intervention: Dict[str, Any]) -> str:
        """Store intervention record"""
        try:
            intervention_entry = {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "intervention": intervention,
                "status": "recommended"
            }
            
            if self.initialized:
                doc_ref = self.db.collection("interventions").add(intervention_entry)
                return doc_ref[1].id
            else:
                interv_id = f"interv_{len(self.mock_db['interventions'])}"
                self.mock_db["interventions"][interv_id] = intervention_entry
                return interv_id
        except Exception as e:
            print(f"ERROR logging intervention: {e}")
            return ""
    
    def update_intervention_status(self, intervention_id: str, status: str, feedback: Optional[str] = None) -> bool:
        """Update intervention completion status"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now().isoformat()
            }
            
            if feedback:
                update_data["user_feedback"] = feedback
            
            if self.initialized:
                self.db.collection("interventions").document(intervention_id).update(update_data)
            else:
                if intervention_id in self.mock_db["interventions"]:
                    self.mock_db["interventions"][intervention_id].update(update_data)
            
            return True
        except Exception as e:
            print(f"ERROR updating intervention: {e}")
            return False
    
    def get_interventions(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve interventions for user"""
        try:
            if self.initialized:
                docs = self.db.collection("interventions")\
                    .where("user_id", "==", user_id)\
                    .order_by("timestamp", direction="DESCENDING")\
                    .limit(limit)\
                    .stream()
                return [doc.to_dict() for doc in docs]
            else:
                user_intervs = [interv for interv in self.mock_db["interventions"].values() 
                               if interv.get("user_id") == user_id]
                return sorted(user_intervs, key=lambda x: x["timestamp"], reverse=True)[:limit]
        except Exception as e:
            print(f"ERROR getting interventions: {e}")
            return []
    
    # ============ ANALYTICS OPERATIONS ============
    
    def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """Get health summary for user"""
        try:
            user = self.get_user(user_id)
            recent_logs = self.get_health_logs(user_id, limit=7)
            recent_interventions = self.get_interventions(user_id, limit=5)
            
            # Calculate averages
            if recent_logs:
                avg_sleep = sum(log["data"].get("sleep_hours", 0) for log in recent_logs) / len(recent_logs)
                avg_steps = sum(log["data"].get("steps", 0) for log in recent_logs) / len(recent_logs)
            else:
                avg_sleep = avg_steps = 0
            
            return {
                "user_id": user_id,
                "user_info": user,
                "recent_health_logs": recent_logs,
                "recent_interventions": recent_interventions,
                "averages": {
                    "sleep_hours": round(avg_sleep, 1),
                    "steps": int(avg_steps)
                },
                "total_interventions": len(recent_interventions)
            }
        except Exception as e:
            print(f"ERROR getting user summary: {e}")
            return {}
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users (admin function)"""
        try:
            if self.initialized:
                docs = self.db.collection("users").stream()
                return [doc.to_dict() for doc in docs]
            else:
                return list(self.mock_db["users"].values())
        except Exception as e:
            print(f"ERROR getting all users: {e}")
            return []
    
    # ============ BATCH OPERATIONS ============
    
    def batch_log_health_data(self, user_id: str, health_data_list: List[Dict[str, Any]]) -> int:
        """Log multiple health data points"""
        count = 0
        for data in health_data_list:
            if self.log_health_data(user_id, data):
                count += 1
        return count
    
    # ============ EXPORT OPERATIONS ============
    
    def export_user_data(self, user_id: str, filepath: str = "user_export.json") -> bool:
        """Export all user data to JSON"""
        try:
            summary = self.get_user_summary(user_id)
            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=2)
            return True
        except Exception as e:
            print(f"ERROR exporting user data: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Check Firebase connection status"""
        return {
            "initialized": self.initialized,
            "mode": "production" if self.initialized else "mock",
            "timestamp": datetime.now().isoformat()
        }


# Initialize Firebase service
firebase_service = FirebaseService()

if __name__ == "__main__":
    # Test operations
    test_user_id = "test_user_001"
    
    # Create user
    firebase_service.create_user(test_user_id, {
        "name": "Test User",
        "email": "test@example.com",
        "age": 28
    })
    
    # Log health data
    firebase_service.log_health_data(test_user_id, {
        "sleep_hours": 7,
        "steps": 8000,
        "mood": "positive"
    })
    
    # Get summary
    summary = firebase_service.get_user_summary(test_user_id)
    print("User Summary:")
    print(json.dumps(summary, indent=2))
