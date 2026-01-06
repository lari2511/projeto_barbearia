# --- ARQUIVO: app/payments.py ---
# Sistema de pagamentos (Stripe e Mercado Pago)

import os
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

# Configurações
STRIPE_KEY = os.getenv("STRIPE_SECRET_KEY")
MERCADOPAGO_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "stripe")  # 'stripe' ou 'mercadopago'

class PaymentService:
    """Serviço de pagamentos abstrato"""
    
    def __init__(self, provider: str = PAYMENT_PROVIDER):
        self.provider = provider
    
    def criar_pagamento(
        self,
        valor: float,
        descricao: str,
        cliente_email: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Cria intenção de pagamento"""
        if self.provider == "stripe":
            return self._stripe_criar_pagamento(valor, descricao, cliente_email, metadata)
        elif self.provider == "mercadopago":
            return self._mercadopago_criar_pagamento(valor, descricao, cliente_email, metadata)
        else:
            raise ValueError(f"Provider '{self.provider}' não suportado")
    
    def confirmar_pagamento(self, payment_id: str) -> bool:
        """Confirma se pagamento foi aprovado"""
        if self.provider == "stripe":
            return self._stripe_confirmar_pagamento(payment_id)
        elif self.provider == "mercadopago":
            return self._mercadopago_confirmar_pagamento(payment_id)
        return False
    
    def estornar_pagamento(self, payment_id: str, valor: Optional[float] = None) -> bool:
        """Estorna pagamento total ou parcial"""
        if self.provider == "stripe":
            return self._stripe_estornar_pagamento(payment_id, valor)
        elif self.provider == "mercadopago":
            return self._mercadopago_estornar_pagamento(payment_id, valor)
        return False
    
    # ===== STRIPE =====
    
    def _stripe_criar_pagamento(
        self, valor: float, descricao: str, cliente_email: str, metadata: Optional[Dict]
    ) -> Dict:
        """Cria Payment Intent no Stripe"""
        try:
            import stripe
            stripe.api_key = STRIPE_KEY
            
            intent = stripe.PaymentIntent.create(
                amount=int(valor * 100),  # Stripe usa centavos
                currency="brl",
                description=descricao,
                receipt_email=cliente_email,
                metadata=metadata or {}
            )
            
            return {
                "payment_id": intent.id,
                "client_secret": intent.client_secret,
                "status": intent.status,
                "provider": "stripe"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _stripe_confirmar_pagamento(self, payment_id: str) -> bool:
        """Verifica status do Payment Intent"""
        try:
            import stripe
            stripe.api_key = STRIPE_KEY
            
            intent = stripe.PaymentIntent.retrieve(payment_id)
            return intent.status == "succeeded"
        except:
            return False
    
    def _stripe_estornar_pagamento(self, payment_id: str, valor: Optional[float]) -> bool:
        """Cria refund no Stripe"""
        try:
            import stripe
            stripe.api_key = STRIPE_KEY
            
            kwargs = {"payment_intent": payment_id}
            if valor:
                kwargs["amount"] = int(valor * 100)
            
            refund = stripe.Refund.create(**kwargs)
            return refund.status == "succeeded"
        except:
            return False
    
    # ===== MERCADO PAGO =====
    
    def _mercadopago_criar_pagamento(
        self, valor: float, descricao: str, cliente_email: str, metadata: Optional[Dict]
    ) -> Dict:
        """Cria preferência de pagamento no Mercado Pago"""
        try:
            import mercadopago
            sdk = mercadopago.SDK(MERCADOPAGO_TOKEN)
            
            preference_data = {
                "items": [{
                    "title": descricao,
                    "quantity": 1,
                    "unit_price": valor
                }],
                "payer": {"email": cliente_email},
                "metadata": metadata or {}
            }
            
            preference_response = sdk.preference().create(preference_data)
            preference = preference_response["response"]
            
            return {
                "payment_id": preference["id"],
                "init_point": preference["init_point"],  # URL de pagamento
                "status": "pending",
                "provider": "mercadopago"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _mercadopago_confirmar_pagamento(self, payment_id: str) -> bool:
        """Verifica status do pagamento"""
        try:
            import mercadopago
            sdk = mercadopago.SDK(MERCADOPAGO_TOKEN)
            
            payment = sdk.payment().get(payment_id)
            return payment["response"]["status"] == "approved"
        except:
            return False
    
    def _mercadopago_estornar_pagamento(self, payment_id: str, valor: Optional[float]) -> bool:
        """Cria refund no Mercado Pago"""
        try:
            import mercadopago
            sdk = mercadopago.SDK(MERCADOPAGO_TOKEN)
            
            refund_data = {}
            if valor:
                refund_data["amount"] = valor
            
            refund = sdk.refund().create(payment_id, refund_data)
            return refund["status"] == 201
        except:
            return False


# Instância global
payment_service = PaymentService()
