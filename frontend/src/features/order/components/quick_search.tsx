import { Search, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { MenuItem } from '@/features/menu/menu_hooks'

interface QuickSearchProps {
  isOpen: boolean
  onClose: () => void
  menuItems: MenuItem[]
  onSelectItem: (item: MenuItem) => void
}

export default function QuickSearch({
  isOpen,
  onClose,
  menuItems,
  onSelectItem,
}: QuickSearchProps) {
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isOpen) {
      setQuery('')
      // Small timeout to allow render and autofocus
      setTimeout(() => {
        inputRef.current?.focus()
      }, 50)
    }
  }, [isOpen])

  // Handle key listeners (ESC)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  if (!isOpen) return null

  // Filter items matching query
  const filtered =
    query.trim() === ''
      ? []
      : menuItems
          .filter(
            (item) =>
              item.name.toLowerCase().includes(query.toLowerCase()) ||
              item.category.toLowerCase().includes(query.toLowerCase()) ||
              item.description?.toLowerCase().includes(query.toLowerCase()),
          )
          .slice(0, 5) // Limit to top 5 results for fast touch targeting

  // Deterministic helper to get a menu item's price
  const getItemPrice = (item: MenuItem): number => {
    try {
      const pricesStr = localStorage.getItem('cf_menu_item_prices')
      if (pricesStr) {
        const prices = JSON.parse(pricesStr)
        if (prices[item.id] !== undefined) {
          return Number(prices[item.id])
        }
      }
    } catch (_e) {
      // Ignore and fallback
    }
    const base = 12.0
    const offset = (item.id % 6) * 5.5
    return base + offset
  }

  return (
    <div className="fixed inset-0 z-55 flex items-start justify-center p-4 bg-black/60 backdrop-blur-sm pt-20 animate-fade-in">
      <div className="w-full max-w-lg rounded-2xl glass-elevated overflow-hidden border border-gray-800">
        {/* Search Input Bar */}
        <div className="relative border-b border-gray-900/60 bg-gray-950/20">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Digite para buscar itens no cardápio..."
            className="w-full bg-transparent pl-12 pr-12 py-4.5 text-sm text-white placeholder-gray-500 focus:outline-none"
          />
          <button
            type="button"
            onClick={onClose}
            className="absolute right-4 top-1/2 -translate-y-1/2 rounded-lg p-1 text-gray-500 hover:text-gray-200 transition hover:bg-white/[0.03]"
          >
            <X className="h-4.5 w-4.5" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-[350px] overflow-y-auto p-2 space-y-1">
          {query.trim() === '' ? (
            <div className="py-8 text-center text-xs text-gray-500">
              Digite alguma letra para começar a pesquisar
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-8 text-center text-xs text-gray-500">
              Nenhum item encontrado para "{query}"
            </div>
          ) : (
            filtered.map((item) => {
              const price = getItemPrice(item)
              return (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => {
                    onSelectItem(item)
                    onClose()
                  }}
                  className="w-full flex items-center justify-between rounded-xl px-4 py-3 text-left transition hover:bg-white/[0.03] group border border-transparent hover:border-gray-850"
                >
                  <div className="space-y-0.5">
                    <span className="text-[9px] font-extrabold uppercase tracking-wider text-brand-400">
                      {item.category}
                    </span>
                    <h4 className="text-xs font-bold text-gray-100 group-hover:text-white transition">
                      {item.name}
                    </h4>
                    {item.description && (
                      <p className="text-[10px] text-gray-500 truncate max-w-xs md:max-w-md">
                        {item.description}
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-black text-amber-500">R$ {price.toFixed(2)}</span>
                    <span className="block text-[8px] text-gray-500 font-medium mt-0.5">
                      Toque para adicionar
                    </span>
                  </div>
                </button>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
