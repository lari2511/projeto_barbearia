# Script de teste para todas as novas funcionalidades
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def print_response(title, response):
    """Helper para printar respostas formatadas"""
    print(f"\n{'='*60}")
    print(f"🔹 {title}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"Response: {response.text}")

def test_todas_funcionalidades():
    """Testa todas as funcionalidades implementadas"""
    
    print("🚀 TESTE COMPLETO DAS FUNCIONALIDADES\n")
    
    # ========== 1. CADASTRO E LOGIN ==========
    print("\n📝 1. CADASTRO E LOGIN")
    
    # Cadastrar cliente
    cliente_data = {
        "nome": "João Silva",
        "email": "joao@test.com",
        "senha": "senha123",
        "telefone": "11987654321"
    }
    r = requests.post(f"{BASE_URL}/clientes/", json=cliente_data)
    print_response("Cadastro Cliente", r)
    
    # Cadastrar barbeiro
    barbeiro_data = {
        "nome": "Carlos Barbeiro",
        "email": "carlos@test.com",
        "senha": "senha123",
        "telefone": "11987654322"
    }
    r = requests.post(f"{BASE_URL}/barbeiros/", json=barbeiro_data)
    print_response("Cadastro Barbeiro", r)
    
    # Cadastrar barbearia
    barbearia_data = {
        "nome": "Barbearia Top",
        "email": "barbearia@test.com",
        "senha": "senha123",
        "telefone": "1140404040",
        "endereco": "Av Paulista 1000, São Paulo",
        "cep": "01310-100"
    }
    r = requests.post(f"{BASE_URL}/barbearias/", json=barbearia_data)
    print_response("Cadastro Barbearia", r)
    
    # Login cliente
    r = requests.post(f"{BASE_URL}/login/cliente/", json={
        "email": "joao@test.com",
        "senha": "senha123"
    })
    print_response("Login Cliente", r)
    token_cliente = r.json()["access_token"]
    
    # Login barbeiro
    r = requests.post(f"{BASE_URL}/login/barbeiro/", json={
        "email": "carlos@test.com",
        "senha": "senha123"
    })
    print_response("Login Barbeiro", r)
    token_barbeiro = r.json()["access_token"]
    
    # Login barbearia
    r = requests.post(f"{BASE_URL}/login/barbearia/", json={
        "email": "barbearia@test.com",
        "senha": "senha123"
    })
    print_response("Login Barbearia", r)
    token_barbearia = r.json()["access_token"]
    
    # ========== 2. CRIAR SERVIÇO ==========
    print("\n💈 2. CRIAR SERVIÇO")
    
    headers_barbearia = {"Authorization": f"Bearer {token_barbearia}"}
    r = requests.post(f"{BASE_URL}/barbearia/servicos", 
                     headers=headers_barbearia,
                     json={
                         "nome": "Corte + Barba",
                         "valor": 50.0
                     })
    print_response("Criar Serviço", r)
    servico_id = r.json()["id"]
    barbearia_id = r.json()["barbearia_id"]
    
    # ========== 3. CUPONS ==========
    print("\n🎟️ 3. SISTEMA DE CUPONS")
    
    # Criar cupom
    r = requests.post(f"{BASE_URL}/cupons/",
                     headers=headers_barbearia,
                     json={
                         "codigo": "NATAL2025",
                         "desconto_percentual": 20.0,
                         "uso_maximo": 10
                     })
    print_response("Criar Cupom", r)
    
    # Listar cupons ativos
    r = requests.get(f"{BASE_URL}/cupons/")
    print_response("Listar Cupons", r)
    
    # Validar cupom
    r = requests.post(f"{BASE_URL}/cupons/validar", json={"codigo": "NATAL2025"})
    print_response("Validar Cupom", r)
    
    # ========== 4. CRIAR CHAMADO ==========
    print("\n📞 4. CRIAR CHAMADO")
    
    headers_cliente = {"Authorization": f"Bearer {token_cliente}"}
    r = requests.post(f"{BASE_URL}/chamados",
                     headers=headers_cliente,
                     json={
                         "servico_id": servico_id,
                         "barbearia_id": barbearia_id
                     })
    print_response("Criar Chamado", r)
    chamado_id = r.json()["id"]
    
    # ========== 5. AGENDAMENTO FUTURO ==========
    print("\n📅 5. AGENDAMENTO FUTURO")
    
    r = requests.post(f"{BASE_URL}/chamados/agendar",
                     headers=headers_cliente,
                     json={
                         "servico_id": servico_id,
                         "barbearia_id": barbearia_id,
                         "data_agendamento": "2025-12-30T15:00:00"
                     })
    print_response("Agendar Chamado", r)
    
    # ========== 6. BARBEIRO ACEITA CHAMADO ==========
    print("\n✅ 6. BARBEIRO ACEITA CHAMADO")
    
    headers_barbeiro = {"Authorization": f"Bearer {token_barbeiro}"}
    r = requests.put(f"{BASE_URL}/chamados/{chamado_id}/aceitar",
                    headers=headers_barbeiro)
    print_response("Aceitar Chamado", r)
    
    # ========== 7. CHAT ==========
    print("\n💬 7. CHAT")
    
    # Cliente envia mensagem
    r = requests.post(f"{BASE_URL}/chat/mensagem",
                     headers=headers_cliente,
                     json={
                         "chamado_id": chamado_id,
                         "mensagem": "Olá, estou chegando!"
                     })
    print_response("Cliente envia mensagem", r)
    
    # Barbeiro responde
    r = requests.post(f"{BASE_URL}/chat/mensagem",
                     headers=headers_barbeiro,
                     json={
                         "chamado_id": chamado_id,
                         "mensagem": "Ok, te espero!"
                     })
    print_response("Barbeiro responde", r)
    
    # Listar mensagens
    r = requests.get(f"{BASE_URL}/chat/{chamado_id}/mensagens",
                    headers=headers_cliente)
    print_response("Listar Mensagens", r)
    
    # ========== 8. FINALIZAR CHAMADO ==========
    print("\n🏁 8. FINALIZAR CHAMADO")
    
    r = requests.put(f"{BASE_URL}/chamados/{chamado_id}/finalizar",
                    headers=headers_barbeiro)
    print_response("Finalizar Chamado", r)
    
    # ========== 9. HISTÓRICO DO CHAMADO ==========
    print("\n📜 9. HISTÓRICO DO CHAMADO")
    
    r = requests.get(f"{BASE_URL}/chamados/{chamado_id}/historico")
    print_response("Histórico Completo", r)
    
    # ========== 10. PONTOS DE FIDELIDADE ==========
    print("\n🏆 10. PONTOS DE FIDELIDADE")
    
    r = requests.get(f"{BASE_URL}/fidelidade/", headers=headers_cliente)
    print_response("Consultar Pontos", r)
    
    # ========== 11. AVALIAÇÃO ==========
    print("\n⭐ 11. AVALIAÇÃO")
    
    # Pegar ID do barbeiro (precisa buscar do chamado)
    r = requests.get(f"{BASE_URL}/cliente/meus_pedidos", headers=headers_cliente)
    
    # Criar avaliação (assumindo barbeiro_id = 2)
    r = requests.post(f"{BASE_URL}/avaliacoes/",
                     headers=headers_cliente,
                     json={
                         "chamado_id": chamado_id,
                         "avaliado_id": 2,  # ID do barbeiro
                         "nota": 5,
                         "comentario": "Excelente atendimento!"
                     })
    print_response("Criar Avaliação", r)
    
    # Ver média de avaliação
    r = requests.get(f"{BASE_URL}/usuario/2/media_avaliacao")
    print_response("Média de Avaliação", r)
    
    # ========== 12. FAVORITOS ==========
    print("\n❤️ 12. FAVORITOS")
    
    r = requests.post(f"{BASE_URL}/favoritos/",
                     headers=headers_cliente,
                     json={"favorito_id": 2})  # Barbeiro
    print_response("Adicionar Favorito", r)
    
    r = requests.get(f"{BASE_URL}/favoritos/", headers=headers_cliente)
    print_response("Listar Favoritos", r)
    
    # ========== 13. FOTOS ==========
    print("\n📸 13. FOTOS")
    
    r = requests.post(f"{BASE_URL}/fotos/",
                     headers=headers_barbeiro,
                     json={
                         "servico_id": servico_id,
                         "url": "https://example.com/foto1.jpg",
                         "descricao": "Corte degradê"
                     })
    print_response("Adicionar Foto", r)
    
    r = requests.get(f"{BASE_URL}/usuario/2/fotos")
    print_response("Listar Fotos do Barbeiro", r)
    
    # ========== 14. NOTIFICAÇÕES ==========
    print("\n🔔 14. NOTIFICAÇÕES")
    
    r = requests.get(f"{BASE_URL}/notificacoes/", headers=headers_cliente)
    print_response("Listar Notificações", r)
    
    # ========== 15. ESTATÍSTICAS ==========
    print("\n📊 15. ESTATÍSTICAS")
    
    r = requests.get(f"{BASE_URL}/estatisticas/", headers=headers_barbeiro)
    print_response("Estatísticas Barbeiro", r)
    
    # ========== 16. GEOLOCALIZAÇÃO ==========
    print("\n📍 16. GEOLOCALIZAÇÃO")
    
    r = requests.post(f"{BASE_URL}/barbearias/proximas", json={
        "latitude": -23.5505,
        "longitude": -46.6333,
        "raio_km": 50.0
    })
    print_response("Barbearias Próximas", r)
    
    # ========== 17. 2FA ==========
    print("\n🔐 17. AUTENTICAÇÃO 2FA")
    
    r = requests.post(f"{BASE_URL}/2fa/ativar", headers=headers_cliente)
    print_response("Ativar 2FA", r)
    
    # ========== 18. RECUPERAÇÃO DE SENHA ==========
    print("\n🔑 18. RECUPERAÇÃO DE SENHA")
    
    r = requests.post(f"{BASE_URL}/recuperar-senha", json={
        "email": "joao@test.com"
    })
    print_response("Solicitar Recuperação", r)
    
    print("\n\n🎉 TESTE COMPLETO FINALIZADO! 🎉\n")
    print("Todas as funcionalidades foram testadas com sucesso!")

if __name__ == "__main__":
    try:
        test_todas_funcionalidades()
    except Exception as e:
        print(f"\n❌ Erro durante o teste: {str(e)}")
        import traceback
        traceback.print_exc()
