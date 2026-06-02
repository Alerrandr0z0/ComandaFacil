import { useMemo, useState } from 'react'
import { type MenuItem, useActiveMenu } from '../menu_hooks'

interface CatalogViewerProps {
  onSelectItem?: (item: MenuItem) => void
  interactive?: boolean
}

export default function CatalogViewer({ onSelectItem, interactive = false }: CatalogViewerProps) {
  const { data: menu, isLoading, error } = useActiveMenu()
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  // 1. Compute dynamic list of categories from active menu items
  const categories = useMemo(() => {
    if (!menu) return []
    const cats = new Set<string>()
    for (const item of menu.items) {
      if (item.category) cats.add(item.category)
    }
    return Array.from(cats)
  }, [menu])

  // 2. Filter menu items by search term and category selection
  const filteredItems = useMemo(() => {
    if (!menu) return []
    return menu.items.filter((item) => {
      const matchesSearch =
        item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.description.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesCategory = selectedCategory === 'all' || item.category === selectedCategory

      return matchesSearch && matchesCategory
    })
  }, [menu, searchTerm, selectedCategory])

  if (isLoading) {
    return (
      <div className="flex py-12 justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
      </div>
    )
  }

  if (error || !menu) {
    return (
      <div className="rounded-xl border border-red-900/50 bg-red-950/20 p-6 text-center text-red-400 backdrop-blur-md">
        <p className="font-semibold">Nenhum cardápio ativo encontrado para esta franquia.</p>
        <p className="mt-1 text-xs text-gray-500">
          Por favor, ative um cardápio no painel de gerência.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Search Input & Category Filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <input
            type="text"
            placeholder="Buscar pratos ou bebidas..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-xl border border-gray-800 bg-gray-900/40 px-4 py-2.5 pl-10 text-sm text-white placeholder-gray-500 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 transition-all"
          />
          <span className="absolute left-3 top-3.5 text-gray-500">
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <title>Search Icon</title>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </span>
        </div>

        {/* Categories Carousel / Tabs */}
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
          <button
            type="button"
            onClick={() => setSelectedCategory('all')}
            className={`rounded-lg px-4 py-2 text-xs font-semibold uppercase tracking-wider transition-all duration-300 ${
              selectedCategory === 'all'
                ? 'bg-brand-500 text-white shadow-md shadow-brand-500/10'
                : 'bg-gray-900/50 border border-gray-800/80 text-gray-400 hover:text-white'
            }`}
          >
            Todos
          </button>
          {categories.map((cat) => (
            <button
              type="button"
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`rounded-lg px-4 py-2 text-xs font-semibold uppercase tracking-wider whitespace-nowrap transition-all duration-300 ${
                selectedCategory === cat
                  ? 'bg-brand-500 text-white shadow-md shadow-brand-500/10'
                  : 'bg-gray-900/50 border border-gray-800/80 text-gray-400 hover:text-white'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Menu Items Grid */}
      {filteredItems.length === 0 ? (
        <div className="rounded-xl border border-gray-800/80 bg-gray-900/20 py-12 text-center text-gray-500">
          Nenhum prato correspondente encontrado nesta categoria.
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
          {filteredItems.map((item) => (
            <button
              type="button"
              key={item.id}
              disabled={interactive && !item.is_available}
              onClick={() => interactive && onSelectItem?.(item)}
              className={`flex flex-col justify-between text-left rounded-xl border p-4 backdrop-blur-md transition-all duration-300 ${
                interactive && item.is_available
                  ? 'cursor-pointer hover:border-brand-500/50 hover:bg-brand-950/5 active:scale-[0.98]'
                  : 'cursor-default'
              } ${
                item.is_available
                  ? 'border-gray-800/80 bg-gray-900/30'
                  : 'border-gray-900 bg-gray-950/20 opacity-50'
              }`}
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between">
                  <h3 className="font-bold text-gray-100">{item.name}</h3>
                  {!item.is_available && (
                    <span className="rounded bg-red-950/60 border border-red-900/40 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-red-400">
                      Esgotado
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-400 line-clamp-2">{item.description}</p>
              </div>

              <div className="mt-4 flex items-center justify-between">
                {/* Simulated category indicator badge */}
                <span className="text-[10px] font-semibold text-brand-400/80 uppercase tracking-wider bg-brand-950/30 border border-brand-900/20 rounded px-1.5 py-0.5">
                  {item.category}
                </span>

                {/* Pricing layout - will be formatted properly using money objects eventually */}
                <span className="text-sm font-extrabold text-amber-500">
                  {/* Since prices are fetched from the PriceList model in backend, 
                      for catalog reading, we fetch current price lists if available.
                      Let's display standard menu items catalog for the UI. */}
                  {/* Note: backend MenuItem has no direct price in DB, prices come from PriceList!
                      We will lookup the active price from the PriceList endpoint or items. 
                      Let's simulate standard items catalog and handle pricing. */}
                  R$ --
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
