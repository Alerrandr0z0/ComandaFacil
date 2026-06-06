import { Check, X } from 'lucide-react'
import { useEffect, useState } from 'react'

interface ModifierPickerProps {
  isOpen: boolean
  onClose: () => void
  itemName: string
  category: string
  initialNotes: string
  onConfirm: (notes: string) => void
}

function parseInitialNotes(initialNotes: string, availableChips: string[]) {
  const parsedNotes = initialNotes ? initialNotes.split(', ').map((n) => n.trim()) : []
  const chips: string[] = []
  const customParts: string[] = []

  for (const note of parsedNotes) {
    if (availableChips.includes(note)) {
      chips.push(note)
    } else if (note) {
      customParts.push(note)
    }
  }

  return { chips, customNotes: customParts.join(', ') }
}

function getModifiersForCategory(category: string): string[] {
  const cat = category.toLowerCase()
  if (
    cat.includes('bebida') ||
    cat.includes('suco') ||
    cat.includes('drink') ||
    cat.includes('cerveja')
  ) {
    return ['Com Gelo', 'Sem Gelo', 'Com Limão', 'Sem Limão', 'Temperatura Ambiente', 'Gelada']
  }
  if (
    cat.includes('carne') ||
    cat.includes('grelhado') ||
    cat.includes('picanha') ||
    cat.includes('filé')
  ) {
    return ['Mal Passado', 'Ao Ponto', 'Bem Passado', 'Sem Cebola', 'Com Fritas', 'Sem Osso']
  }
  // General modifiers
  return ['Sem Cebola', 'Sem Alho', 'Sem Pimenta', 'Sem Sal', 'Porção Dupla', 'Embalagem p/ Viagem']
}

export default function ModifierPicker({
  isOpen,
  onClose,
  itemName,
  category,
  initialNotes,
  onConfirm,
}: ModifierPickerProps) {
  const [selectedModifiers, setSelectedModifiers] = useState<string[]>([])
  const [customNotes, setCustomNotes] = useState('')

  const modifiers = getModifiersForCategory(category)

  useEffect(() => {
    if (isOpen) {
      const availableChips = getModifiersForCategory(category)
      const { chips, customNotes: parsedCustom } = parseInitialNotes(initialNotes, availableChips)
      setSelectedModifiers(chips)
      setCustomNotes(parsedCustom)
    }
  }, [isOpen, initialNotes, category])

  if (!isOpen) return null

  const handleToggleModifier = (modifier: string) => {
    setSelectedModifiers((prev) =>
      prev.includes(modifier) ? prev.filter((m) => m !== modifier) : [...prev, modifier],
    )
  }

  const handleSave = () => {
    const parts = [...selectedModifiers]
    if (customNotes.trim()) {
      parts.push(customNotes.trim())
    }
    onConfirm(parts.join(', '))
    onClose()
  }

  return (
    <div className="fixed inset-0 z-55 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md rounded-2xl glass-elevated overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-900/60 p-4">
          <div>
            <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">
              Modificadores
            </h3>
            <p className="text-sm font-bold text-white mt-0.5">{itemName}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-500 hover:text-gray-200 transition bg-white/[0.03]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-6">
          {/* Quick Modifier Chips */}
          <div className="space-y-2.5">
            <span className="block text-[10px] uppercase tracking-wider font-extrabold text-brand-400">
              Atalhos Rápidos
            </span>
            <div className="grid grid-cols-2 gap-2">
              {modifiers.map((mod) => {
                const isSelected = selectedModifiers.includes(mod)
                return (
                  <button
                    type="button"
                    key={mod}
                    onClick={() => handleToggleModifier(mod)}
                    className={`flex items-center justify-between rounded-xl px-4 py-3 text-xs font-bold border transition-all duration-300 ${
                      isSelected
                        ? 'bg-brand-500/10 border-brand-500/30 text-brand-400 shadow-md shadow-brand-500/5'
                        : 'border-gray-850 bg-gray-900/10 text-gray-400 hover:text-white hover:border-gray-800'
                    }`}
                  >
                    <span>{mod}</span>
                    {isSelected && <Check className="h-3.5 w-3.5 text-brand-400" />}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Custom free text notes */}
          <div className="space-y-2.5">
            <span className="block text-[10px] uppercase tracking-wider font-extrabold text-brand-400">
              Observações Customizadas
            </span>
            <textarea
              value={customNotes}
              onChange={(e) => setCustomNotes(e.target.value)}
              placeholder="Digite observações personalizadas (ex: sem coentro, ponto bem passado nas bordas...)"
              className="w-full h-20 rounded-xl px-4 py-3 text-xs text-white placeholder-gray-600 glass-input"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex border-t border-gray-900/60 p-4 gap-3 bg-gray-950/20">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-xl border border-gray-800 hover:bg-white/[0.02] py-3 text-xs font-bold text-gray-400 hover:text-white transition duration-200"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="flex-1 rounded-xl bg-brand-500 hover:bg-brand-600 active:scale-[0.98] py-3 text-xs font-bold text-white transition duration-200 shadow-lg shadow-brand-500/10"
          >
            Aplicar
          </button>
        </div>
      </div>
    </div>
  )
}
