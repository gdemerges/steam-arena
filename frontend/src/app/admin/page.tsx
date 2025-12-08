'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ArrowLeftIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import { syncPopularGenres, syncAllGenres } from '@/lib/api'

export default function AdminPage() {
  const [syncingAll, setSyncingAll] = useState(false)
  const [syncingPopular, setSyncingPopular] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSyncAllGenres = async () => {
    if (!confirm('Cette opération peut prendre beaucoup de temps (plusieurs heures pour des milliers de jeux). Continuer ?')) {
      return
    }

    setSyncingAll(true)
    setResult(null)
    setError(null)
    try {
      const res = await syncAllGenres(1.5)
      setResult(res.data)
      alert(`Synchronisation terminée!\nSynchronisés: ${res.data.synced}\nIgnorés: ${res.data.skipped}\nÉchecs: ${res.data.failed}`)
    } catch (err: any) {
      console.error('Sync failed:', err)
      const errorMsg = err.response?.data?.detail || err.message || 'Erreur inconnue'
      setError(errorMsg)
      alert(`Échec de la synchronisation: ${errorMsg}`)
    } finally {
      setSyncingAll(false)
    }
  }

  const handleSyncPopularGenres = async () => {
    setSyncingPopular(true)
    setResult(null)
    setError(null)
    try {
      const res = await syncPopularGenres(100)
      setResult(res.data)
      alert(`Synchronisation terminée!\nSynchronisés: ${res.data.synced}\nIgnorés: ${res.data.skipped}\nÉchecs: ${res.data.failed}`)
    } catch (err: any) {
      console.error('Sync failed:', err)
      const errorMsg = err.response?.data?.detail || err.message || 'Erreur inconnue'
      setError(errorMsg)
      alert(`Échec de la synchronisation: ${errorMsg}`)
    } finally {
      setSyncingPopular(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/" className="btn-secondary">
          <ArrowLeftIcon className="h-5 w-5" />
        </Link>
        <h1 className="text-3xl font-bold">Administration</h1>
      </div>

      {/* Genre Sync Section */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Synchronisation des Genres</h2>
        <p className="text-gray-400 mb-6">
          Les genres sont récupérés depuis l'API Steam Store. Cette opération est nécessaire pour afficher
          les statistiques par genre et les filtres.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Sync Popular Games */}
          <div className="border border-gray-700 rounded-lg p-4">
            <h3 className="font-semibold mb-2">Jeux Populaires (Rapide)</h3>
            <p className="text-sm text-gray-400 mb-4">
              Synchronise les 100 jeux les plus joués. Temps estimé : ~2-3 minutes.
            </p>
            <button
              onClick={handleSyncPopularGenres}
              disabled={syncingPopular || syncingAll}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {syncingPopular ? (
                <>
                  <ArrowPathIcon className="h-5 w-5 animate-spin" />
                  Synchronisation en cours...
                </>
              ) : (
                <>
                  <ArrowPathIcon className="h-5 w-5" />
                  Sync 100 Jeux Populaires
                </>
              )}
            </button>
          </div>

          {/* Sync All Games */}
          <div className="border border-gray-700 rounded-lg p-4">
            <h3 className="font-semibold mb-2">Tous les Jeux (Lent)</h3>
            <p className="text-sm text-gray-400 mb-4">
              Synchronise TOUS les jeux de la base. ⚠️ Peut prendre plusieurs heures!
            </p>
            <button
              onClick={handleSyncAllGenres}
              disabled={syncingAll || syncingPopular}
              className="btn-secondary w-full flex items-center justify-center gap-2"
            >
              {syncingAll ? (
                <>
                  <ArrowPathIcon className="h-5 w-5 animate-spin" />
                  Synchronisation en cours...
                </>
              ) : (
                <>
                  <ArrowPathIcon className="h-5 w-5" />
                  Sync Tous les Jeux
                </>
              )}
            </button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mt-6 p-4 bg-red-900/20 border border-red-500/30 rounded-lg">
            <h4 className="font-semibold text-red-400 mb-2">❌ Erreur</h4>
            <p className="text-sm text-gray-300">{error}</p>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="mt-6 p-4 bg-green-900/20 border border-green-500/30 rounded-lg">
            <h4 className="font-semibold text-green-400 mb-2">Résultats</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-gray-400">Synchronisés</p>
                <p className="text-xl font-bold text-green-400">{result.synced}</p>
              </div>
              <div>
                <p className="text-gray-400">Ignorés</p>
                <p className="text-xl font-bold text-yellow-400">{result.skipped}</p>
              </div>
              <div>
                <p className="text-gray-400">Échecs</p>
                <p className="text-xl font-bold text-red-400">{result.failed}</p>
              </div>
              <div>
                <p className="text-gray-400">Total vérifié</p>
                <p className="text-xl font-bold text-blue-400">
                  {result.total_checked || result.total_games || 0}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Instructions */}
      <div className="card border border-yellow-500/30 bg-yellow-900/10">
        <h3 className="font-semibold text-yellow-400 mb-2">ℹ️ Informations</h3>
        <ul className="text-sm text-gray-300 space-y-2">
          <li>• Les jeux déjà synchronisés sont automatiquement ignorés</li>
          <li>• Un délai de 1,5 seconde est appliqué entre chaque jeu pour éviter le throttling Steam</li>
          <li>• La synchronisation peut être interrompue sans danger (redémarrage du backend)</li>
          <li>• Les genres sont nécessaires pour : filtres, statistiques par genre, ML analytics</li>
        </ul>
      </div>
    </div>
  )
}
