import { useState, useMemo } from 'react'
import { useGrocery } from '../context/GroceryContext'
import NavButton from '../components/NavButton'
import LeftSidebar from '../components/LeftSidebar'
import { CATEGORY_ORDER, shouldShowQuantity } from '../utils/ingredientCategories'

export default function IngredientManagerPage() {
  const {
    previousRecipes,
    getMergedIngredients,
    toggleMergedChecked,
    getIngredientsByRecipe,
    pantryItems,
  } = useGrocery()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [filterUncheckedOnly, setFilterUncheckedOnly] = useState(false)
  const [filterCheckedOnly, setFilterCheckedOnly] = useState(false)
  const [filterByCategory, setFilterByCategory] = useState(null)
  const [filterByRecipeId, setFilterByRecipeId] = useState(null)

  const mergedIngredients = useMemo(
    () => getMergedIngredients(filterByRecipeId || null),
    [getMergedIngredients, filterByRecipeId]
  )

  const filteredIngredients = useMemo(() => {
    let list = mergedIngredients
    if (filterUncheckedOnly) list = list.filter((i) => !i.checked)
    if (filterCheckedOnly) list = list.filter((i) => i.checked)
    if (filterByCategory) list = list.filter((i) => i.category === filterByCategory)
    return list
  }, [mergedIngredients, filterUncheckedOnly, filterCheckedOnly, filterByCategory])

  const ingredientsByCategory = useMemo(() => {
    const byCategory = new Map()
    CATEGORY_ORDER.forEach((cat) => byCategory.set(cat, []))
    filteredIngredients.forEach((ing) => {
      const cat = ing.category || 'Uncategorized'
      if (!byCategory.has(cat)) byCategory.set(cat, [])
      byCategory.get(cat).push(ing)
    })
    return CATEGORY_ORDER.map((cat) => ({ category: cat, ingredients: byCategory.get(cat) || [] })).filter(
      (group) => group.ingredients.length > 0
    )
  }, [filteredIngredients])

  // Effective "need to buy" = recipe count minus what's in pantry
  const getEffectiveNeed = (mergedKey) => {
    const ing = mergedIngredients.find((i) => i.mergedKey === mergedKey)
    if (!ing) return 0
    const pantryQty = pantryItems[mergedKey]?.quantity ?? 0
    return Math.max(0, (Number(ing.recipeCount) || 0) - Number(pantryQty))
  }

  return (
    <div className="page ingredient-manager-page">
      <NavButton />

      <div className="ingredient-manager-layout">
        <div className="left-sidebar-wrap">
          <LeftSidebar
            isOpen={sidebarOpen}
            onToggle={() => setSidebarOpen((o) => !o)}
            filterByRecipeId={filterByRecipeId}
            onFilterByRecipe={setFilterByRecipeId}
          />
        </div>

        <div className="ingredient-manager-main">
          <div className="ingredient-manager-grid">
            <main className="ingredient-list-column card">
              <h2 className="ingredient-list-title">Grocery list</h2>
              <div className="filter-bar">
                <div className="filter-group filter-group-inline">
                  <label className="filter-checkbox">
                    <input
                      type="checkbox"
                      checked={filterUncheckedOnly}
                      onChange={(e) => {
                        setFilterUncheckedOnly(e.target.checked)
                        if (e.target.checked) setFilterCheckedOnly(false)
                      }}
                    />
                    <span>Unchecked only</span>
                  </label>
                  <label className="filter-checkbox">
                    <input
                      type="checkbox"
                      checked={filterCheckedOnly}
                      onChange={(e) => {
                        setFilterCheckedOnly(e.target.checked)
                        if (e.target.checked) setFilterUncheckedOnly(false)
                      }}
                    />
                    <span>Checked only</span>
                  </label>
                </div>
                <div className="filter-group filter-group-inline">
                  <label className="filter-label">Category</label>
                  <select
                    className="filter-select"
                    value={filterByCategory ?? ''}
                    onChange={(e) => setFilterByCategory(e.target.value || null)}
                    aria-label="Filter by category"
                  >
                    <option value="">All categories</option>
                    {CATEGORY_ORDER.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="ingredient-list-scroll">
                {filteredIngredients.length === 0 ? (
                  <p className="empty-state">
                    {mergedIngredients.length === 0
                      ? 'No ingredients yet. Add a recipe from the Recipe Input page.'
                      : 'No ingredients match the current filters.'}
                  </p>
                ) : (
                  <div className="ingredient-list-by-category">
                    {ingredientsByCategory.map(({ category, ingredients }) => (
                      <section key={category} className="ingredient-category-section">
                        <h3 className="ingredient-category-heading">{category}</h3>
                        <ul className="ingredient-rows">
                          {ingredients.map((ing) => {
                            const effectiveNeed = getEffectiveNeed(ing.mergedKey)
                            return (
                              <li
                                key={ing.mergedKey}
                                className={`ingredient-row ${effectiveNeed === 0 ? 'ingredient-row--have-enough' : ''}`}
                              >
                                <label className="ingredient-checkbox">
                                  <input
                                    type="checkbox"
                                    checked={ing.checked}
                                    onChange={() => toggleMergedChecked(ing.mergedKey)}
                                    aria-label={`Mark ${ing.name} as done`}
                                  />
                                </label>
                                <span className="ingredient-name">{ing.name}</span>
                                {shouldShowQuantity(ing.category) ? (
                                  <span
                                    className="ingredient-recipe-count"
                                    title={
                                      effectiveNeed === 0
                                        ? 'You have enough in pantry'
                                        : `Need ${effectiveNeed} (in ${ing.recipeCount} recipe${ing.recipeCount !== 1 ? 's' : ''})`
                                    }
                                  >
                                    {effectiveNeed === 0 ? '✓' : effectiveNeed}
                                  </span>
                                ) : (
                                  <span className="ingredient-recipe-count ingredient-recipe-count--no-qty" aria-hidden="true" />
                                )}
                              </li>
                            )
                          })}
                        </ul>
                      </section>
                    ))}
                  </div>
                )}
              </div>
            </main>
          </div>
        </div>
      </div>
    </div>
  )
}
