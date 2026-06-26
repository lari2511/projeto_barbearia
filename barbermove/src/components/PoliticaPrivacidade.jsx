import React from 'react';
import { ArrowLeft, Shield, Lock, Database, UserCheck } from 'lucide-react';

export default function PoliticaPrivacidade({ onVoltar }) {
  return (
    <div className="h-full overflow-y-auto bg-black py-8 px-4">
      <div className="max-w-4xl mx-auto bg-zinc-900 rounded-lg shadow-lg p-8 border border-zinc-800">
        {onVoltar && (
          <button
            onClick={onVoltar}
            className="flex items-center text-orange-500 hover:text-orange-400 mb-6"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Voltar
          </button>
        )}

        <div className="flex items-center gap-3 mb-6">
          <Shield className="w-10 h-10 text-orange-500" />
          <h1 className="text-3xl font-bold text-white">
            Política de Privacidade
          </h1>
        </div>
        <p className="text-sm text-zinc-400 mb-8">
          <strong>Última atualização:</strong> Janeiro de 2026
        </p>
        
        <div className="prose max-w-none space-y-6 text-zinc-300">
          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">1. Introdução</h2>
            <p>
              O <strong>BarberMove</strong> respeita sua privacidade e está comprometido em proteger 
              seus dados pessoais conforme a <strong>Lei Geral de Proteção de Dados (LGPD - Lei 13.709/2018)</strong>.
            </p>
            <div className="bg-blue-900/20 border-l-4 border-orange-500 p-4 my-4">
              <p className="font-semibold text-white">Esta Política explica:</p>
              <ul className="list-disc pl-6 mt-2 space-y-1">
                <li>Quais dados coletamos</li>
                <li>Como usamos seus dados</li>
                <li>Com quem compartilhamos</li>
                <li>Seus direitos sobre seus dados</li>
                <li>Como protegemos suas informações</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Database className="w-6 h-6 text-blue-600" />
              2. Dados que Coletamos
            </h2>
            
            <h3 className="text-xl font-semibold text-gray-800 mt-4 mb-2">2.1 Dados de Cadastro</h3>
            <ul className="list-disc pl-6 space-y-1">
              <li>Nome completo</li>
              <li>CPF</li>
              <li>E-mail</li>
              <li>Telefone</li>
              <li>Data de nascimento</li>
              <li>Endereço</li>
              <li>Foto de perfil</li>
            </ul>

            <h3 className="text-xl font-semibold text-gray-800 mt-4 mb-2">2.2 Dados de Verificação</h3>
            <p className="text-sm text-gray-600 mb-2">(Para Barbeiros e Barbearias)</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>RG ou CNH (frente e verso)</li>
              <li>Selfie com documento</li>
              <li>Registro profissional</li>
              <li>Comprovante de endereço</li>
              <li>Fotos/vídeos de trabalhos anteriores</li>
            </ul>

            <h3 className="text-xl font-semibold text-gray-800 mt-4 mb-2">2.3 Dados de Localização</h3>
            <ul className="list-disc pl-6 space-y-1">
              <li>Geolocalização em tempo real (apenas durante uso ativo)</li>
              <li>Endereço de barbearias</li>
              <li>Histórico de check-ins</li>
              <li>Rotas e distâncias</li>
            </ul>

            <h3 className="text-xl font-semibold text-gray-800 mt-4 mb-2">2.4 Dados Financeiros</h3>
            <ul className="list-disc pl-6 space-y-1">
              <li>Dados de cartão (tokenizados e criptografados)</li>
              <li>Chaves PIX</li>
              <li>Histórico de transações</li>
              <li>Cupons e descontos utilizados</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">3. Como Usamos Seus Dados</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="bg-green-50 p-3 rounded">✅ Criar e gerenciar sua conta</div>
              <div className="bg-green-50 p-3 rounded">✅ Facilitar agendamentos</div>
              <div className="bg-green-50 p-3 rounded">✅ Processar pagamentos</div>
              <div className="bg-green-50 p-3 rounded">✅ Verificar identidade</div>
              <div className="bg-green-50 p-3 rounded">✅ Enviar notificações</div>
              <div className="bg-green-50 p-3 rounded">✅ Melhorar a experiência</div>
              <div className="bg-green-50 p-3 rounded">✅ Cumprir obrigações legais</div>
              <div className="bg-green-50 p-3 rounded">✅ Análises estatísticas</div>
            </div>

            <h3 className="text-xl font-semibold text-gray-800 mt-4 mb-2">Base Legal (LGPD)</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Execução de contrato:</strong> Necessário para fornecer o serviço</li>
              <li><strong>Consentimento:</strong> Para envio de ofertas e marketing</li>
              <li><strong>Legítimo interesse:</strong> Prevenir fraudes e melhorar a plataforma</li>
              <li><strong>Obrigação legal:</strong> Cumprir leis fiscais e tributárias</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">4. Compartilhamento de Dados</h2>
            
            <div className="bg-green-50 border-l-4 border-green-400 p-4 mb-4">
              <p className="font-semibold mb-2">✅ Compartilhamos com:</p>
              <ul className="list-disc pl-6 space-y-1 text-sm">
                <li><strong>Barbeiros:</strong> Nome, foto e telefone do cliente agendado</li>
                <li><strong>Clientes:</strong> Nome, foto e avaliações do barbeiro</li>
                <li><strong>Barbearias:</strong> Dados de agendamentos em seu espaço</li>
                <li><strong>Gateways de Pagamento:</strong> Dados financeiros criptografados</li>
                <li><strong>Autoridades:</strong> Mediante ordem judicial</li>
              </ul>
            </div>

            <div className="bg-red-50 border-l-4 border-red-400 p-4">
              <p className="font-semibold mb-2">❌ NÃO Compartilhamos:</p>
              <ul className="list-disc pl-6 space-y-1 text-sm">
                <li>Não vendemos seus dados para terceiros</li>
                <li>Não enviamos dados para fins publicitários externos</li>
                <li>Não compartilhamos com parceiros sem consentimento</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Lock className="w-6 h-6 text-blue-600" />
              5. Proteção de Dados
            </h2>
            
            <h3 className="text-xl font-semibold text-gray-800 mt-4 mb-2">Medidas de Segurança</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              <div className="flex items-center gap-2 bg-blue-50 p-2 rounded">
                <Lock className="w-4 h-4 text-blue-600" />
                <span className="text-sm">Criptografia SSL/TLS</span>
              </div>
              <div className="flex items-center gap-2 bg-blue-50 p-2 rounded">
                <Lock className="w-4 h-4 text-blue-600" />
                <span className="text-sm">Senhas com hash bcrypt</span>
              </div>
              <div className="flex items-center gap-2 bg-blue-50 p-2 rounded">
                <Lock className="w-4 h-4 text-blue-600" />
                <span className="text-sm">Tokens JWT seguros</span>
              </div>
              <div className="flex items-center gap-2 bg-blue-50 p-2 rounded">
                <Lock className="w-4 h-4 text-blue-600" />
                <span className="text-sm">Firewall e proteção DDoS</span>
              </div>
              <div className="flex items-center gap-2 bg-blue-50 p-2 rounded">
                <Lock className="w-4 h-4 text-blue-600" />
                <span className="text-sm">Backups criptografados</span>
              </div>
              <div className="flex items-center gap-2 bg-blue-50 p-2 rounded">
                <Lock className="w-4 h-4 text-blue-600" />
                <span className="text-sm">Monitoramento 24/7</span>
              </div>
            </div>

            <h3 className="text-xl font-semibold text-gray-800 mt-4 mb-2">Retenção de Dados</h3>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>Dados de conta ativa:</strong> Mantidos enquanto a conta existir</li>
              <li><strong>Após exclusão:</strong> Dados anonimizados em 30 dias</li>
              <li><strong>Dados financeiros:</strong> Mantidos por 5 anos (obrigação legal)</li>
              <li><strong>Backups:</strong> Removidos após 90 dias</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <UserCheck className="w-6 h-6 text-blue-600" />
              6. Seus Direitos (LGPD)
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-gray-200 p-4 rounded-lg">
                <h3 className="font-semibold text-gray-800 mb-2">📄 Acesso</h3>
                <p className="text-sm">Solicitar cópia de todos os dados que temos sobre você</p>
              </div>
              
              <div className="border border-gray-200 p-4 rounded-lg">
                <h3 className="font-semibold text-gray-800 mb-2">✏️ Correção</h3>
                <p className="text-sm">Corrigir dados incorretos ou desatualizados</p>
              </div>
              
              <div className="border border-gray-200 p-4 rounded-lg">
                <h3 className="font-semibold text-gray-800 mb-2">🗑️ Exclusão</h3>
                <p className="text-sm">Solicitar exclusão de sua conta e dados pessoais</p>
              </div>
              
              <div className="border border-gray-200 p-4 rounded-lg">
                <h3 className="font-semibold text-gray-800 mb-2">📦 Portabilidade</h3>
                <p className="text-sm">Receber seus dados em formato estruturado (JSON/CSV)</p>
              </div>
              
              <div className="border border-gray-200 p-4 rounded-lg">
                <h3 className="font-semibold text-gray-800 mb-2">🚫 Revogação</h3>
                <p className="text-sm">Cancelar consentimento para marketing</p>
              </div>
              
              <div className="border border-gray-200 p-4 rounded-lg">
                <h3 className="font-semibold text-gray-800 mb-2">⛔ Oposição</h3>
                <p className="text-sm">Opor-se ao tratamento para finalidades específicas</p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">7. Como Exercer Seus Direitos</h2>
            <div className="bg-blue-50 p-6 rounded-lg">
              <p className="font-semibold mb-3">Para exercer qualquer direito acima:</p>
              <ul className="space-y-2">
                <li className="flex items-center gap-2">
                  <span className="text-2xl">📧</span>
                  <span><strong>E-mail:</strong> privacidade@barbermove.com</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-2xl">📱</span>
                  <span><strong>Pelo App:</strong> Configurações → Privacidade e Dados</span>
                </li>
              </ul>
              <p className="mt-4 text-sm"><strong>Prazo de resposta:</strong> Até 15 dias úteis</p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">8. Menores de Idade</h2>
            <div className="bg-red-50 border-l-4 border-red-400 p-4">
              <p className="font-semibold mb-2">
                ❌ O BarberMove <strong>NÃO</strong> permite cadastro de menores de 18 anos.
              </p>
              <p className="text-sm">
                Se identificarmos conta de menor de idade, a conta será suspensa imediatamente e os dados excluídos.
              </p>
            </div>
          </section>

          <section className="bg-blue-50 p-6 rounded-lg mt-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Encarregado de Dados (DPO)</h2>
            <ul className="space-y-1">
              <li>📧 <strong>E-mail:</strong> privacidade@barbermove.com</li>
              <li>📞 <strong>Telefone:</strong> (XX) XXXX-XXXX</li>
            </ul>
            <p className="text-sm mt-3 text-gray-600">
              O DPO é responsável por atender solicitações de titulares, orientar sobre LGPD e interagir com a ANPD.
            </p>
          </section>

          <section className="bg-gray-50 p-6 rounded-lg mt-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Reclamações</h2>
            <p className="mb-2">Se não estiver satisfeito com nossa resposta, você pode reclamar à:</p>
            <div className="bg-zinc-900 p-4 rounded border border-zinc-800">
              <p className="font-semibold text-white">🏛️ ANPD (Autoridade Nacional de Proteção de Dados)</p>
              <p className="text-sm mt-1 text-zinc-300">Site: www.gov.br/anpd</p>
              <p className="text-sm text-zinc-300">E-mail: comunicacao@anpd.gov.br</p>
            </div>
          </section>

          <div className="bg-gray-100 p-4 rounded-lg mt-6 text-center">
            <p className="text-sm text-gray-600">
              <strong>Versão:</strong> 1.0 | <strong>Data:</strong> Janeiro de 2026
            </p>
            <p className="text-xs text-gray-500 mt-2">
              Ao criar uma conta e usar o BarberMove, você declara ter lido e compreendido esta Política de Privacidade 
              e concorda com a coleta e tratamento de dados conforme descrito.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
