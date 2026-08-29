import React, { useMemo, useState } from 'react';
import AvaliacaoModal from './AvaliacaoModal';

/**
 * Fluxo automatico de avaliacao do cliente apos o pagamento confirmado.
 * Dois passos independentes e sequenciais: primeiro o freelancer, depois a barbearia.
 * Reaproveita o AvaliacaoModal. Pula o passo que ja foi enviado.
 */
export default function FluxoAvaliacaoCliente({ pendencia, API_URL, token, notify, onDone }) {
    const passosIniciais = useMemo(() => {
        const lista = [];
        if (pendencia && !pendencia.avaliacao_freelancer_enviada) lista.push('freelancer');
        if (pendencia && !pendencia.avaliacao_barbearia_enviada) lista.push('barbearia');
        return lista;
    }, [pendencia]);

    const [indice, setIndice] = useState(0);
    const passoAtual = passosIniciais[indice] || null;

    if (!pendencia || !passoAtual) return null;

    const enviar = async ({ nota, comentario }) => {
        const alvo = passoAtual === 'freelancer'
            ? `/api/v1/avaliacoes/freelancer/${pendencia.freelancer_id || pendencia.freelancer_usuario_id}`
            : `/api/v1/avaliacoes/barbearia/${pendencia.barbearia_id}`;

        try {
            const res = await fetch(`${API_URL}${alvo}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    chamado_id: pendencia.chamado_id,
                    nota,
                    comentario: comentario || null,
                }),
            });

            if (!res.ok) {
                const erro = await res.json().catch(() => ({}));
                notify?.(erro.detail || 'Nao foi possivel enviar a avaliacao', 'error');
                return false;
            }

            const temProximo = indice + 1 < passosIniciais.length;
            notify?.(
                temProximo
                    ? 'Freelancer avaliado. Agora avalie a barbearia.'
                    : 'Avaliacao concluida. Obrigado!',
                'success',
            );

            if (temProximo) {
                // Avanca para o proximo passo mantendo o modal aberto.
                // Retornar false impede o AvaliacaoModal de fechar sozinho.
                setIndice(indice + 1);
                return false;
            }
            onDone?.();
            return true;
        } catch (_err) {
            notify?.('Erro de conexao ao enviar avaliacao', 'error');
            return false;
        }
    };

    const fechar = () => {
        // Fechar nao desfaz nada; os passos restantes seguem acessiveis na aba "Avaliar".
        onDone?.();
    };

    const ehFreelancer = passoAtual === 'freelancer';

    return (
        <AvaliacaoModal
            isOpen
            onClose={fechar}
            onSubmit={enviar}
            titulo={ehFreelancer ? 'Avaliar Freelancer' : 'Avaliar Barbearia'}
            subtitulo={ehFreelancer ? 'Como foi o atendimento do profissional?' : 'Como foi sua experiencia na barbearia?'}
            avatarUrl={ehFreelancer ? pendencia.freelancer_foto : pendencia.barbearia_foto}
            nomeAlvo={ehFreelancer ? pendencia.freelancer_nome : pendencia.barbearia_nome}
            textoBotao={ehFreelancer ? 'Avaliar freelancer' : 'Avaliar barbearia'}
        />
    );
}
