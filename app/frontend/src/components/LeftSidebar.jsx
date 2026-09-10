import { useState, useMemo } from 'react'
import { useGrocery } from '../context/GroceryContext'
import {
  CATEGORY_ORDER,
  KNOWN_INGREDIENTS,
  getCategory,
  shouldShowQuantity,
} from '../utils/ingredientCategories'

const SIDEBAR_TABS = { PANTRY: 'pantry', RECIPES: 'recipes' }

function capitalize(str) {
  if (!str || typeof str !== 'string') return str
  return str.replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function LeftSidebar({ isOpen, onToggle, filterByRecipeId, onFilterByRecipe }) {
  const {
    previousRecipes,
    getIngredientsByRecipe,
    updateRecipeQuantity,
    applyRecipeQuantities,
    pantryItems,
    addPantryItem,
    removePantryItem,
    updatePantryQuantity,
  } = useGrocery()
  const [activeTab, setActiveTab] = useState(SIDEBAR_TABS.PANTRY)
  const [pantrySearch, setPantrySearch] = useState('')
  const [expandedRecipeId, setExpandedRecipeId] = useState(null)

  const pantryList = useMemo(() => {
    return Object.entries(pantryItems).map(([key, { name, quantity }]) => ({
      key,
      name,
      quantity,
      category: getCategory(key),
    }))
  }, [pantryItems])

  const pantryByCategory = useMemo(() => {
    const byCategory = new Map()
    CATEGORY_ORDER.forEach((cat) => byCategory.set(cat, []))
    pantryList.forEach((item) => {
      const cat = item.category || 'Uncategorized'
      if (!byCategory.has(cat)) byCategory.set(cat, [])
      byCategory.get(cat).push(item)
    })
    return CATEGORY_ORDER.map((cat) => ({ category: cat, items: byCategory.get(cat) || [] })).filter(
      (group) => group.items.length > 0
    )
  }, [pantryList])

  const searchSuggestions = useMemo(() => {
    if (!pantrySearch.trim()) return []
    const q = pantrySearch.toLowerCase().trim()
    return KNOWN_INGREDIENTS.filter((ing) => ing.includes(q)).slice(0, 8)
  }, [pantrySearch])

  const canAddCustom = pantrySearch.trim() && !searchSuggestions.includes(pantrySearch.toLowerCase().trim())

  const toggleAccordion = (recipeId) => {
    setExpandedRecipeId((prev) => (prev === recipeId ? null : recipeId))
  }

  const handleAddPantry = (normalizedKey, displayName) => {
    addPantryItem(normalizedKey, displayName || capitalize(normalizedKey), 1)
  }

  return (
    <>
      <button
        type="button"
        className="sidebar-toggle"
        onClick={onToggle}
        aria-expanded={isOpen}
        aria-label={isOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        {isOpen ? '‹' : '›'}
      </button>

      <aside className={`left-sidebar card ${isOpen ? 'left-sidebar--open' : ''}`} aria-hidden={!isOpen}>
        <nav className="sidebar-nav" aria-label="Sidebar sections">
          <button
            type="button"
            className={`sidebar-nav-btn ${activeTab === SIDEBAR_TABS.PANTRY ? 'sidebar-nav-btn--active' : ''}`}
            onClick={() => setActiveTab(SIDEBAR_TABS.PANTRY)}
          >
            Pantry
          </button>
          <button
            type="button"
            className={`sidebar-nav-btn ${activeTab === SIDEBAR_TABS.RECIPES ? 'sidebar-nav-btn--active' : ''}`}
            onClick={() => setActiveTab(SIDEBAR_TABS.RECIPES)}
          >
            Recipes
          </button>
        </nav>

        {activeTab === SIDEBAR_TABS.PANTRY && (
          <div className="sidebar-panel sidebar-panel-pantry">
            <div className="pantry-search-wrap">
              <input
                type="text"
                className="input-box pantry-search"
                placeholder="Search ingredients to add…"
                value={pantrySearch}
                onChange={(e) => setPantrySearch(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && canAddCustom) {
                    e.preventDefault()
                    handleAddPantry(pantrySearch.trim().toLowerCase(), pantrySearch.trim())
                  }
                }}
                aria-label="Search ingredients for pantry"
                autoComplete="off"
              />
              {searchSuggestions.length > 0 && (
                <ul className="pantry-suggestions" role="listbox">
                  {searchSuggestions.map((ing) => {
                    const inPantry = !!pantryItems[ing]
                    return (
                      <li key={ing}>
                        <button
                          type="button"
                          className={`pantry-suggestion-btn ${inPantry ? 'pantry-suggestion-btn--in-pantry' : ''}`}
                          onClick={() => !inPantry && handleAddPantry(ing, capitalize(ing))}
                          role="option"
                          disabled={inPantry}
                          title={inPantry ? 'Already in pantry' : undefined}
                        >
                          {capitalize(ing)}{' '}
                          {inPantry ? (
                            <span className="pantry-suggestion-in-pantry">In pantry</span>
                          ) : (
                            <span className="pantry-suggestion-add">+ Add</span>
                          )}
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
              {canAddCustom && (
                <button
                  type="button"
                  className="pantry-add-custom-btn"
                  onClick={() => handleAddPantry(pantrySearch.trim().toLowerCase(), pantrySearch.trim())}
                >
                  Add &quot;{pantrySearch.trim()}&quot; to pantry
                </button>
              )}
            </div>
            <div className="pantry-list-scroll">
              {pantryByCategory.length === 0 ? (
                <p className="sidebar-empty">Your pantry is empty. Search above to add ingredients you already have.</p>
              ) : (
                <div className="pantry-by-category">
                  {pantryByCategory.map(({ category, items }) => (
                    <section key={category} className="ingredient-category-section">
                      <h3 className="ingredient-category-heading">{category}</h3>
                      <ul className="ingredient-rows">
                        {items.map((item) => (
                          <li key={item.key} className="ingredient-row pantry-row">
                            <span className="ingredient-name">{item.name}</span>
                            {shouldShowQuantity(item.category) ? (
                              <div className="pantry-qty-wrap">
                                <input
                                  type="number"
                                  min={1}
                                  value={item.quantity}
                                  onChange={(e) => updatePantryQuantity(item.key, e.target.value)}
                                  className="ingredient-quantity-input pantry-qty-input"
                                  aria-label={`Quantity for ${item.name}`}
                                />
                              </div>
                            ) : (
                              <span className="ingredient-recipe-count ingredient-recipe-count--no-qty" aria-hidden="true" />
                            )}
                            <button
                              type="button"
                              className="pantry-remove-btn"
                              onClick={() => removePantryItem(item.key)}
                              aria-label={`Remove ${item.name} from pantry`}
                              title="Remove from pantry"
                            >
                              ×
                            </button>
                          </li>
                        ))}
                      </ul>
                    </section>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === SIDEBAR_TABS.RECIPES && (
          <div className="sidebar-panel sidebar-panel-recipes">
            <h2 className="sidebar-title">Previous recipes</h2>
            {previousRecipes.length === 0 ? (
              <p className="sidebar-empty">No recipes yet. Add one from the Recipe Input page.</p>
            ) : (
              <div className="accordion-section accordion-section-scrollable">
                <div className="accordion-list-scroll">
                  {previousRecipes.map((recipe) => {
                    const isOpen = expandedRecipeId === recipe.id
                    const count = getIngredientsByRecipe(recipe.id).length
                    return (
                      <div key={recipe.id} className="accordion-item recipe-card">
                        <button
                          type="button"
                          className="accordion-trigger recipe-trigger"
                          onClick={() => toggleAccordion(recipe.id)}
                          aria-expanded={isOpen}
                        >
                          <div className="recipe-thumbnail-wrap">
                            {recipe.thumbnail ? (
                              <img src={recipe.thumbnail} alt="" className="recipe-thumbnail" />
                            ) : (
                              <div className="recipe-thumbnail-placeholder" />
                            )}
                          </div>
                          <div className="recipe-meta">
                            <span className="recipe-title">{recipe.title || recipe.label}</span>
                            <span className="recipe-ingredient-count">{count} ingredients</span>
                            <div className="recipe-quantity-row">
                              <label className="recipe-quantity-label">Qty:</label>
                              <input
                                type="number"
                                min={0}
                                value={recipe.quantity}
                                onChange={(e) => {
                                  e.stopPropagation()
                                  updateRecipeQuantity(recipe.id, e.target.value)
                                }}
                                onClick={(e) => e.stopPropagation()}
                                className="recipe-quantity-input"
                                aria-label={`Quantity for ${recipe.title || recipe.label}`}
                              />
                            </div>
                          </div>
                          <span className="accordion-icon">{isOpen ? '−' : '+'}</span>
                          <label
                            className="recipe-include-checkbox"
                            onClick={(e) => e.stopPropagation()}
                            title={recipe.quantity > 0 ? 'Exclude from grocery list' : 'Include in grocery list'}
                          >
                            <input
                                type="checkbox"
                                checked={recipe.quantity > 0}
                                onChange={() => {
                                  updateRecipeQuantity(recipe.id, recipe.quantity > 0 ? 0 : 1)
                                }}
                              aria-label={recipe.quantity > 0 ? 'Exclude recipe from list' : 'Include recipe in list'}
                            />
                          </label>
                        </button>
                        {isOpen && (
                          <div className="accordion-content">
                            {onFilterByRecipe && (
                              <button
                                type="button"
                                className="filter-by-recipe-btn"
                                onClick={() => onFilterByRecipe(filterByRecipeId === recipe.id ? null : recipe.id)}
                              >
                                {filterByRecipeId === recipe.id ? 'Show all' : 'Show only these'}
                              </button>
                            )}
                            <ul className="accordion-list">
                              {getIngredientsByRecipe(recipe.id).map((ing, idx) => (
                                <li key={`${ing.recipeId}-${idx}`} className="accordion-label">
                                  {ing.name}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
                <div className="accordion-actions">
                  <button type="button" className="update-quantities-btn" onClick={applyRecipeQuantities}>
                    Update quantities
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </aside>
    </>
  )
}
