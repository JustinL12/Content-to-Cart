import { createContext, useContext, useState, useCallback, useMemo, useEffect } from 'react'
import { getCategory } from '../utils/ingredientCategories'

const GroceryContext = createContext(null)
const PANTRY_STORAGE_KEY = 'grocery-pantry'

let nextRecipeId = 1

function loadPantry() {
  try {
    const raw = localStorage.getItem(PANTRY_STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return typeof parsed === 'object' && parsed !== null ? parsed : {}
  } catch {
    return {}
  }
}

function savePantry(items) {
  try {
    localStorage.setItem(PANTRY_STORAGE_KEY, JSON.stringify(items))
  } catch {}
}

function normalizeQuantity(qty) {
  if (qty == null || String(qty).toLowerCase().trim() === 'unknown') return ''
  return String(qty).trim()
}

export function GroceryProvider({ children }) {
  const [previousRecipes, setPreviousRecipes] = useState([])
  // Per-merged-ingredient overrides: key = normalized name (lowercase trim)
  const [mergedOverrides, setMergedOverrides] = useState({})
  // Bump to force grocery list to recalc from recipe quantities (e.g. after "Update quantities")
  const [applyVersion, setApplyVersion] = useState(0)
  // Pantry: items user already has. key = normalized name, value = { name, quantity }
  const [pantryItems, setPantryItems] = useState(loadPantry)

  useEffect(() => {
    savePantry(pantryItems)
  }, [pantryItems])

  const addRecipe = useCallback((url, extracted) => {
    const raw = extracted?.ingredients || extracted || []
    const baseIngredients = raw.map((item) => ({
      name: item.ingredient ?? item.name ?? String(item),
      quantity: normalizeQuantity(item.quantity),
    }))
    const label = url.replace(/^https?:\/\/(www\.)?/, '').split('/')[0] || 'Recipe'
    const title = (extracted?.title && String(extracted.title).trim()) || label
    const thumbnail = extracted?.thumbnail ?? ''

    setPreviousRecipes((prev) => {
      const existing = prev.find((r) => r.url === url)
      if (existing) {
        return prev.map((r) =>
          r.url === url ? { ...r, quantity: r.quantity + 1 } : r
        )
      }
      const recipeId = `recipe-${nextRecipeId++}`
      return [
        ...prev,
        {
          id: recipeId,
          url,
          label,
          title,
          thumbnail,
          quantity: 1,
          baseIngredients,
          addedAt: Date.now(),
        },
      ]
    })
  }, [])

  const updateRecipeQuantity = useCallback((recipeId, quantity) => {
    const n = Math.max(0, Math.floor(Number(quantity)) || 0)
    setPreviousRecipes((prev) =>
      prev.map((r) => (r.id === recipeId ? { ...r, quantity: n } : r))
    )
  }, [])

  const getMergedIngredients = useCallback(
    (filterByRecipeId = null) => {
      const expanded = []
      previousRecipes.forEach((recipe) => {
        if (filterByRecipeId && recipe.id !== filterByRecipeId) return
        recipe.baseIngredients.forEach((ing) => {
          for (let i = 0; i < recipe.quantity; i++) {
            expanded.push({
              name: ing.name,
              quantity: ing.quantity,
              recipeId: recipe.id,
            })
          }
        })
      })
      const byName = new Map()
      expanded.forEach(({ name }) => {
        const key = name.toLowerCase().trim()
        if (!byName.has(key)) {
          byName.set(key, { name, totalQuantity: 0 })
        }
        byName.get(key).totalQuantity += 1
      })
      return Array.from(byName.entries()).map(([key, { name, totalQuantity }]) => {
        const override = mergedOverrides[key]
        return {
          mergedKey: key,
          name,
          recipeCount: totalQuantity,
          quantity: String(totalQuantity),
          checked: override?.checked ?? false,
          category: getCategory(key),
        }
      })
    },
    [previousRecipes, mergedOverrides, applyVersion]
  )

  const applyRecipeQuantities = useCallback(() => {
    setApplyVersion((v) => v + 1)
  }, [])

  const updateMergedQuantity = useCallback((mergedKey, quantity) => {
    setMergedOverrides((prev) => ({
      ...prev,
      [mergedKey]: { ...prev[mergedKey], quantity: String(quantity) },
    }))
  }, [])

  const toggleMergedChecked = useCallback((mergedKey) => {
    setMergedOverrides((prev) => ({
      ...prev,
      [mergedKey]: { ...prev[mergedKey], checked: !prev[mergedKey]?.checked },
    }))
  }, [])

  const getIngredientsByRecipe = useCallback(
    (recipeId) => {
      const recipe = previousRecipes.find((r) => r.id === recipeId)
      if (!recipe) return []
      return recipe.baseIngredients.map((ing) => ({
        ...ing,
        recipeId,
      }))
    },
    [previousRecipes]
  )

  const addPantryItem = useCallback((normalizedKey, displayName, quantity = 1) => {
    const key = normalizedKey.toLowerCase().trim()
    const name = (displayName && displayName.trim()) || key
    setPantryItems((prev) => {
      const existing = prev[key]
      const newQty = (existing ? Number(existing.quantity) || 0 : 0) + Math.max(0, Number(quantity) || 1)
      return { ...prev, [key]: { name, quantity: newQty } }
    })
  }, [])

  const removePantryItem = useCallback((normalizedKey) => {
    const key = normalizedKey.toLowerCase().trim()
    setPantryItems((prev) => {
      const next = { ...prev }
      delete next[key]
      return next
    })
  }, [])

  const updatePantryQuantity = useCallback((normalizedKey, quantity) => {
    const key = normalizedKey.toLowerCase().trim()
    const qty = Math.max(0, Math.floor(Number(quantity)) || 0)
    setPantryItems((prev) => {
      const item = prev[key]
      if (!item) return prev
      if (qty === 0) {
        const next = { ...prev }
        delete next[key]
        return next
      }
      return { ...prev, [key]: { ...item, quantity: qty } }
    })
  }, [])

  const value = useMemo(
    () => ({
      previousRecipes,
      addRecipe,
      updateRecipeQuantity,
      getMergedIngredients,
      updateMergedQuantity,
      toggleMergedChecked,
      getIngredientsByRecipe,
      applyRecipeQuantities,
      pantryItems,
      addPantryItem,
      removePantryItem,
      updatePantryQuantity,
    }),
    [
      previousRecipes,
      addRecipe,
      updateRecipeQuantity,
      getMergedIngredients,
      updateMergedQuantity,
      toggleMergedChecked,
      getIngredientsByRecipe,
      applyRecipeQuantities,
      pantryItems,
      addPantryItem,
      removePantryItem,
      updatePantryQuantity,
    ]
  )

  return (
    <GroceryContext.Provider value={value}>{children}</GroceryContext.Provider>
  )
}

export function useGrocery() {
  const ctx = useContext(GroceryContext)
  if (!ctx) throw new Error('useGrocery must be used within GroceryProvider')
  return ctx
}
