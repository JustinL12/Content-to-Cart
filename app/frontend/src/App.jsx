import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { GroceryProvider } from './context/GroceryContext'
import RecipeInputPage from './pages/RecipeInputPage'
import IngredientManagerPage from './pages/IngredientManagerPage'
import './App.css'

export default function App() {
  return (
    <GroceryProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/input" element={<RecipeInputPage />} />
          <Route path="/ingredients" element={<IngredientManagerPage />} />
          <Route path="/" element={<Navigate to="/input" replace />} />
          <Route path="*" element={<Navigate to="/input" replace />} />
        </Routes>
      </BrowserRouter>
    </GroceryProvider>
  )
}
