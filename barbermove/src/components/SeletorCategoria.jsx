/**
 * SeletorCategoria.jsx
 * 
 * Componente para selecionar uma categoria de serviço.
 * 
 * Oferece 8 categorias fixas com labels amigáveis:
 * - CORTE → "Corte de Cabelo"
 * - BARBA → "Barba e Bigode"
 * - SOBRANCELHA → "Design de Sobrancelha"
 * - QUIMICA → "Química/Alisamento"
 * - INFANTIL → "Corte Infantil"
 * - TRATAMENTO → "Tratamento Capilar"
 * - COMBO → "Pacote Combo"
 * - OUTROS → "Outros Serviços"
 * 
 * O campo nome é livre (criatividade do dono).
 * A categoria é padrão (para organização e relatórios).
 */

// eslint-disable-next-line react-refresh/only-export-components
export const CATEGORIAS_SERVICOS = [
  { valor: "corte", label: "Corte de Cabelo" },
  { valor: "barba", label: "Barba e Bigode" },
  { valor: "sobrancelha", label: "Design de Sobrancelha" },
  { valor: "quimica", label: "Química/Alisamento" },
  { valor: "infantil", label: "Corte Infantil" },
  { valor: "tratamento", label: "Tratamento Capilar" },
  { valor: "combo", label: "Pacote Combo" },
  { valor: "outros", label: "Outros Serviços" }
];

export default function SeletorCategoria({ 
  valor = "", 
  onChange = () => {},
  label = "Categoria do Serviço",
  obrigatorio = true,
  desabilitado = false,
  className = ""
}) {
  return (
    <div className={`selector-categoria-wrapper ${className}`}>
      <label htmlFor="categoria-select">
        {label}
        {obrigatorio && <span className="required">*</span>}
      </label>
      
      <select
        id="categoria-select"
        value={valor}
        onChange={(e) => onChange(e.target.value)}
        disabled={desabilitado}
        className={`categoria-select ${valor ? "selected" : "placeholder"}`}
        required={obrigatorio}
      >
        <option value="">Escolha uma categoria...</option>
        {CATEGORIAS_SERVICOS.map((cat) => (
          <option key={cat.valor} value={cat.valor}>
            {cat.label}
          </option>
        ))}
      </select>

      <style jsx>{`
        .selector-categoria-wrapper {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        label {
          font-size: 0.875rem;
          font-weight: 600;
          color: #333;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .required {
          color: #e74c3c;
          margin-left: 0.25rem;
        }

        .categoria-select {
          padding: 0.75rem;
          border: 2px solid #e0e0e0;
          border-radius: 6px;
          font-size: 1rem;
          background-color: white;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .categoria-select:hover:not(:disabled) {
          border-color: #9c27b0;
          box-shadow: 0 2px 8px rgba(156, 39, 176, 0.15);
        }

        .categoria-select:focus {
          outline: none;
          border-color: #9c27b0;
          box-shadow: 0 0 0 3px rgba(156, 39, 176, 0.1);
        }

        .categoria-select.selected {
          color: #333;
          font-weight: 500;
        }

        .categoria-select.placeholder {
          color: #999;
        }

        .categoria-select:disabled {
          background-color: #f5f5f5;
          color: #999;
          cursor: not-allowed;
          opacity: 0.6;
        }

        .categoria-select option {
          padding: 0.5rem;
          color: #333;
        }
      `}</style>
    </div>
  );
}
