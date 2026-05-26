import React from 'react';
import { ArrowLeft } from 'lucide-react';

export default function TermosDeUso({ onVoltar }) {
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

        <h1 className="text-3xl font-bold text-white mb-6">
          Termos de Uso, Políticas de Funcionamento e Condições Gerais
        </h1>
        
        <div className="prose max-w-none space-y-6 text-zinc-300">
          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">1. Sobre o BarberMove</h2>
            <p>
              O <strong>BarberMove</strong> é uma plataforma tecnológica de intermediação que conecta 
              Donos de Barbearias, Barbeiros Freelancers e Clientes Finais.
            </p>
            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 my-4">
              <p className="font-semibold">IMPORTANTE:</p>
              <p>
                O BarberMove <strong>NÃO</strong> é empregador, <strong>NÃO</strong> presta serviços 
                de barbearia e <strong>NÃO</strong> cria vínculo empregatício entre as partes.
              </p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">2. Funcionamento Geral</h2>
            <p>A plataforma opera com três perfis distintos:</p>
            
            <h3 className="text-xl font-semibold text-gray-800 mt-4 mb-2">2.1 BARBEARIA</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>Disponibiliza cadeiras, estrutura mínima e insumos básicos</li>
              <li><strong>NÃO</strong> escolhe o profissional — o cliente escolhe livremente</li>
              <li>Recebe uma taxa de locação por uso da cadeira/espaço</li>
              <li>Deve manter o ambiente limpo, seguro e adequado</li>
            </ul>

            <h3 className="text-xl font-semibold text-gray-800 mt-4 mb-2">2.2 BARBEIRO FREELANCER</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>Atua como <strong>profissional autônomo</strong> (Pleno ou Superior)</li>
              <li><strong>OBRIGATÓRIO:</strong> Envio de 3 fotos/vídeos autorais com rosto visível</li>
              <li>Deve portar seus <strong>próprios equipamentos</strong> (máquinas, tesouras, produtos, etc.)</li>
              <li>Deve manter postura ética e profissional</li>
              <li>Responsável por seus próprios tributos e obrigações legais</li>
              <li>Deve possuir registro profissional válido</li>
            </ul>

            <h3 className="text-xl font-semibold text-gray-800 mt-4 mb-2">2.3 CLIENTE</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>Escolhe livremente o barbeiro disponível</li>
              <li>Avalia o serviço prestado após a conclusão</li>
              <li>Realiza pagamento diretamente pelo aplicativo</li>
              <li>Pode cancelar agendamentos conforme política de cancelamento</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">3. Check-in Georreferenciado</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>O profissional <strong>SÓ</strong> pode receber clientes <strong>APÓS</strong> realizar check-in georreferenciado</li>
              <li>O check-in confirma que o barbeiro está fisicamente presente na barbearia</li>
              <li>Evita fraudes e garante segurança para todas as partes</li>
              <li>O check-out deve ser realizado ao finalizar o expediente</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">4. Ausência de Vínculo Empregatício</h2>
            <div className="bg-red-50 border-l-4 border-red-400 p-4">
              <p className="font-semibold mb-2">FICA EXPRESSAMENTE ESTABELECIDO:</p>
              <ul className="list-disc pl-6 space-y-1">
                <li>Não há vínculo empregatício entre BarberMove e Barbeiros</li>
                <li>Não há vínculo empregatício entre Barbearia e Barbeiros</li>
                <li>Não há vínculo empregatício entre BarberMove e Barbearias</li>
                <li>Cada parte é responsável por suas próprias obrigações fiscais, trabalhistas e previdenciárias</li>
                <li>O BarberMove atua exclusivamente como <strong>intermediador tecnológico</strong></li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">5. Pagamentos</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>Todos os pagamentos são processados pela plataforma</li>
              <li>Métodos aceitos: PIX, Cartão de Crédito, Cartão de Débito</li>
              <li>Taxa da plataforma: 10% do valor do serviço</li>
              <li>Taxa da barbearia: 20-30% do valor do serviço (acordado previamente)</li>
              <li>Barbeiro recebe: 60-70% do valor do serviço</li>
              <li>Repasses realizados em até 2 dias úteis após confirmação do serviço</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">6. Cancelamentos e Reembolsos</h2>
            
            <h3 className="text-xl font-semibold text-gray-800 mt-4 mb-2">Cancelamento pelo Cliente:</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>Até 2 horas antes: <strong>reembolso total</strong></li>
              <li>Entre 1-2 horas antes: <strong>reembolso de 50%</strong></li>
              <li>Menos de 1 hora: <strong>sem reembolso</strong></li>
              <li>No-show (não comparecimento): <strong>sem reembolso</strong></li>
            </ul>

            <h3 className="text-xl font-semibold text-gray-800 mt-4 mb-2">Cancelamento pelo Barbeiro:</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>Cliente recebe <strong>reembolso total imediato</strong></li>
              <li>Barbeiro pode receber advertência ou suspensão</li>
              <li>Reincidência pode resultar em banimento</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">7. Verificação de Documentos</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>OBRIGATÓRIO</strong> para barbeiros e barbearias</li>
              <li>Documentos necessários: RG/CNH + Selfie com documento</li>
              <li>Registro profissional válido (quando aplicável)</li>
              <li>Verificação pode levar até 48 horas</li>
              <li>Perfis não verificados têm funcionalidades limitadas</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">8. Penalidades e Suspensões</h2>
            
            <h3 className="text-xl font-semibold text-gray-800 mt-4 mb-2">Motivos para Banimento Permanente:</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>Fraude ou falsificação de documentos</li>
              <li>Comportamento abusivo ou agressivo</li>
              <li>Discriminação (raça, gênero, religião, etc.)</li>
              <li>Atividades ilegais na plataforma</li>
              <li>Violação grave dos termos de uso</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">9. Disposições Finais</h2>
            <p>
              O uso contínuo da plataforma implica <strong>aceitação integral</strong> destes termos.
              Caso alguma cláusula seja considerada inválida, as demais permanecem em vigor.
            </p>
          </section>

          <section className="bg-blue-50 p-6 rounded-lg mt-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Contato</h2>
            <p><strong>BarberMove - Plataforma de Agendamento</strong></p>
            <ul className="space-y-1 mt-2">
              <li>📧 E-mail: suporte@barbermove.com</li>
              <li>📧 E-mail LGPD: privacidade@barbermove.com</li>
              <li>📞 Telefone: (XX) XXXX-XXXX</li>
              <li>🌐 Site: www.barbermove.com</li>
            </ul>
          </section>

          <div className="bg-gray-100 p-4 rounded-lg mt-6 text-center">
            <p className="text-sm text-gray-600">
              <strong>Versão:</strong> 1.0 | <strong>Última Atualização:</strong> Janeiro de 2026
            </p>
            <p className="text-xs text-gray-500 mt-2">
              Ao criar uma conta ou utilizar o BarberMove, você declara que leu, compreendeu e concorda com todos os termos acima.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
