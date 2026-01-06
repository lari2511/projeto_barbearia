#!/usr/bin/env python3
"""
Testes unitários para validar o cálculo de split de pagamento.
Garante que não há perda de centavos e que a soma sempre fecha corretamente.
"""

import pytest
from decimal import Decimal


def calcular_split(valor_total: float) -> dict:
    """
    Calcula o split de pagamento entre plataforma, freelancer e dono da barbearia.
    
    Regras:
    - Plataforma: 15%
    - Freelancer (barbeiro): 45%
    - Dono da barbearia: 40%
    
    Args:
        valor_total: Valor total do serviço em reais
        
    Returns:
        Dict com valores exatos para cada parte
    """
    # Usar Decimal para precisão exata
    total = Decimal(str(valor_total))
    
    # Calcular cada parte com 2 casas decimais
    plataforma = (total * Decimal('0.15')).quantize(Decimal('0.01'))
    freelancer = (total * Decimal('0.45')).quantize(Decimal('0.01'))
    
    # Dono recebe o que sobrar para garantir que a soma seja exata
    dono = total - plataforma - freelancer
    
    return {
        'total': float(total),
        'plataforma': float(plataforma),
        'freelancer': float(freelancer),
        'dono': float(dono),
    }


class TestSplitPagamento:
    """Testes para validar o cálculo de split de pagamento"""
    
    def test_split_50_reais(self):
        """Valida split de R$ 50,00"""
        resultado = calcular_split(50.00)
        
        assert resultado['plataforma'] == 7.50, "Plataforma deve receber R$ 7,50 (15%)"
        assert resultado['freelancer'] == 22.50, "Freelancer deve receber R$ 22,50 (45%)"
        assert resultado['dono'] == 20.00, "Dono deve receber R$ 20,00 (40%)"
        
        # A soma DEVE ser exatamente R$ 50,00
        soma = resultado['plataforma'] + resultado['freelancer'] + resultado['dono']
        assert soma == 50.00, f"Soma deve ser exatamente R$ 50,00, mas foi R$ {soma:.2f}"
    
    def test_split_100_reais(self):
        """Valida split de R$ 100,00"""
        resultado = calcular_split(100.00)
        
        assert resultado['plataforma'] == 15.00, "Plataforma deve receber R$ 15,00 (15%)"
        assert resultado['freelancer'] == 45.00, "Freelancer deve receber R$ 45,00 (45%)"
        assert resultado['dono'] == 40.00, "Dono deve receber R$ 40,00 (40%)"
        
        soma = resultado['plataforma'] + resultado['freelancer'] + resultado['dono']
        assert soma == 100.00, f"Soma deve ser exatamente R$ 100,00, mas foi R$ {soma:.2f}"
    
    def test_split_valor_quebrado(self):
        """Valida split de valor com centavos (R$ 37,50)"""
        resultado = calcular_split(37.50)
        
        # Valores esperados com arredondamento
        esperado_plataforma = 5.62  # 15% de 37.50 = 5.625 → 5.62
        esperado_freelancer = 16.88  # 45% de 37.50 = 16.875 → 16.88
        esperado_dono = 15.00  # Resto para fechar = 37.50 - 5.62 - 16.88
        
        assert resultado['plataforma'] == esperado_plataforma
        assert resultado['freelancer'] == esperado_freelancer
        assert resultado['dono'] == esperado_dono
        
        soma = resultado['plataforma'] + resultado['freelancer'] + resultado['dono']
        assert soma == 37.50, f"Soma deve ser exatamente R$ 37,50, mas foi R$ {soma:.2f}"
    
    def test_split_valor_centavos_complexos(self):
        """Valida split de R$ 33,33 (valor que gera muito arredondamento)"""
        resultado = calcular_split(33.33)
        
        soma = resultado['plataforma'] + resultado['freelancer'] + resultado['dono']
        assert abs(soma - 33.33) < 0.01, f"Soma deve ser R$ 33,33 ±0.01, mas foi R$ {soma:.2f}"
        
        # Verificar que nenhuma parte é negativa
        assert resultado['plataforma'] > 0, "Plataforma deve receber valor positivo"
        assert resultado['freelancer'] > 0, "Freelancer deve receber valor positivo"
        assert resultado['dono'] > 0, "Dono deve receber valor positivo"
    
    def test_split_multiplos_valores(self):
        """Testa vários valores para garantir que a soma sempre fecha"""
        valores_teste = [25.00, 30.00, 45.90, 60.00, 75.50, 89.99, 120.00, 150.00]
        
        for valor in valores_teste:
            resultado = calcular_split(valor)
            soma = resultado['plataforma'] + resultado['freelancer'] + resultado['dono']
            
            assert abs(soma - valor) < 0.01, \
                f"Para R$ {valor:.2f}, soma foi R$ {soma:.2f} (diferença: R$ {abs(soma - valor):.4f})"
    
    def test_split_proporcoes_corretas(self):
        """Valida se as proporções estão próximas dos percentuais esperados"""
        resultado = calcular_split(100.00)
        
        # Tolerância de 1% para arredondamento
        assert 14 <= resultado['plataforma'] <= 16, "Plataforma deve ficar entre 14-16%"
        assert 44 <= resultado['freelancer'] <= 46, "Freelancer deve ficar entre 44-46%"
        assert 39 <= resultado['dono'] <= 41, "Dono deve ficar entre 39-41%"
    
    def test_split_valor_minimo(self):
        """Testa valor mínimo típico (R$ 10,00)"""
        resultado = calcular_split(10.00)
        
        soma = resultado['plataforma'] + resultado['freelancer'] + resultado['dono']
        assert soma == 10.00, f"Soma deve ser exatamente R$ 10,00, mas foi R$ {soma:.2f}"
        
        # Verificar que todos têm valores razoáveis
        assert resultado['plataforma'] >= 1.00, "Plataforma deve receber pelo menos R$ 1,00"
        assert resultado['freelancer'] >= 4.00, "Freelancer deve receber pelo menos R$ 4,00"
        assert resultado['dono'] >= 3.00, "Dono deve receber pelo menos R$ 3,00"
    
    def test_split_sem_perda_centavos(self):
        """Garante que não há perda de centavos em nenhum cálculo"""
        for valor in range(1000, 20000, 100):  # De R$ 10,00 a R$ 200,00
            valor_real = valor / 100.0
            resultado = calcular_split(valor_real)
            
            soma = resultado['plataforma'] + resultado['freelancer'] + resultado['dono']
            diferenca = abs(soma - valor_real)
            
            assert diferenca < 0.01, \
                f"Para R$ {valor_real:.2f}, diferença foi R$ {diferenca:.4f} (máximo aceito: R$ 0.01)"
    
    def test_split_retorna_floats(self):
        """Valida que os valores retornados são floats (não Decimal)"""
        resultado = calcular_split(50.00)
        
        assert isinstance(resultado['total'], float)
        assert isinstance(resultado['plataforma'], float)
        assert isinstance(resultado['freelancer'], float)
        assert isinstance(resultado['dono'], float)


if __name__ == "__main__":
    # Executar testes
    pytest.main([__file__, "-v", "--tb=short"])
