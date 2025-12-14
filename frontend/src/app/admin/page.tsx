'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { ArrowLeftIcon, ArrowPathIcon, ClockIcon, CalendarIcon } from '@heroicons/react/24/outline'
import { 
  syncPopularGenres, 
  syncAllGenres,
  createPlaytimeSnapshot,
  calculateYearlyStats,
  calculateMonthlyStats,
  getSnapshotHistory
} from '@/lib/api'

export default function AdminPage() {
  const [syncingAll, setSyncingAll] = useState(false)
  const [syncingPopular, setSyncingPopular] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  
  // Playtime tracking state
  const [creatingSnapshot, setCreatingSnapshot] = useState(false)
  const [calculatingStats, setCalculatingStats] = useState(false)
  const [calculatingMonthlyStats, setCalculatingMonthlyStats] = useState(false)
  const [snapshotResult, setSnapshotResult] = useState<any>(null)
  const [statsResult, setStatsResult] = useState<any>(null)
  const [monthlyStatsResult, setMonthlyStatsResult] = useState<any>(null)
  const [snapshotHistory, setSnapshotHistory] = useState<any[]>([])
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear())
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1)

  useEffect(() => {
    loadSnapshotHistory()
  }, [])

  const loadSnapshotHistory = async () => {
    try {
      const res = await getSnapshotHistory(10)
      setSnapshotHistory(res.data)
    } catch (err) {
      console.error('Failed to load snapshot history:', err)
    }
  }

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

  const handleCreateSnapshot = async () => {
    setCreatingSnapshot(true)
    setSnapshotResult(null)
    try {
      const res = await createPlaytimeSnapshot()
      setSnapshotResult(res.data)
      alert(`Snapshot créé!\n${res.data.snapshots_created} enregistrements créés`)
      loadSnapshotHistory()
    } catch (err: any) {
      console.error('Snapshot failed:', err)
      const errorMsg = err.response?.data?.detail || err.message || 'Erreur inconnue'
      alert(`Échec du snapshot: ${errorMsg}`)
    } finally {
      setCreatingSnapshot(false)
    }
  }

  const handleCalculateStats = async () => {
    setCalculatingStats(true)
    setStatsResult(null)
    try {
      const res = await calculateYearlyStats(selectedYear)
      setStatsResult(res.data)
      alert(`Stats calculées pour ${selectedYear}!\n${res.data.users_processed} utilisateurs traités`)
    } catch (err: any) {
      console.error('Stats calculation failed:', err)
      const errorMsg = err.response?.data?.detail || err.message || 'Erreur inconnue'
      alert(`Échec du calcul: ${errorMsg}`)
    } finally {
      setCalculatingStats(false)
    }
  }

  const handleCalculateMonthlyStats = async () => {
    setCalculatingMonthlyStats(true)
    setMonthlyStatsResult(null)
    try {
      const res = await calculateMonthlyStats(selectedYear, selectedMonth)
      setMonthlyStatsResult(res.data)
      alert(`Stats mensuelles calculées!\n${res.data.users_processed} utilisateurs traités pour ${res.data.month}/${res.data.year}`)
    } catch (err: any) {
      console.error('Monthly stats calculation failed:', err)
      const errorMsg = err.response?.data?.detail || err.message || 'Erreur inconnue'
      alert(`Échec du calcul: ${errorMsg}`)
    } finally {
      setCalculatingMonthlyStats(false)
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

      {/* Playtime Tracking Section */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">📊 Tracking du Temps de Jeu</h2>
        <p className="text-gray-400 mb-6">
          Crée des snapshots du temps de jeu pour suivre l'évolution dans le temps et calculer
          les statistiques annuelles.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {/* Create Snapshot */}
          <div className="border border-gray-700 rounded-lg p-4">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <ClockIcon className="h-5 w-5 text-blue-400" />
              Créer un Snapshot
            </h3>
            <p className="text-sm text-gray-400 mb-4">
              Enregistre le temps de jeu actuel de tous les utilisateurs. Recommandé : quotidien.
            </p>
            <button
              onClick={handleCreateSnapshot}
              disabled={creatingSnapshot}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {creatingSnapshot ? (
                <>
                  <ArrowPathIcon className="h-5 w-5 animate-spin" />
                  Création en cours...
                </>
              ) : (
                <>
                  <ClockIcon className="h-5 w-5" />
                  Créer Snapshot Maintenant
                </>
              )}
            </button>
          </div>

          {/* Calculate Yearly Stats */}
          <div className="border border-gray-700 rounded-lg p-4">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <CalendarIcon className="h-5 w-5 text-purple-400" />
              Calculer Stats Annuelles
            </h3>
            <p className="text-sm text-gray-400 mb-4">
              Calcule les statistiques pour une année à partir des snapshots.
            </p>
            <div className="flex gap-2 mb-2">
              <select 
                value={selectedYear} 
                onChange={(e) => setSelectedYear(Number(e.target.value))}
                className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              >
                {[2025, 2024, 2023, 2022, 2021].map(year => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>
            <button
              onClick={handleCalculateStats}
              disabled={calculatingStats}
              className="btn-secondary w-full flex items-center justify-center gap-2"
            >
              {calculatingStats ? (
                <>
                  <ArrowPathIcon className="h-5 w-5 animate-spin" />
                  Calcul en cours...
                </>
              ) : (
                <>
                  <CalendarIcon className="h-5 w-5" />
                  Calculer pour {selectedYear}
                </>
              )}
            </button>
          </div>

          {/* Calculate Monthly Stats */}
          <div className="border border-gray-700 rounded-lg p-4">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <CalendarIcon className="h-5 w-5 text-green-400" />
              Calculer Stats Mensuelles
            </h3>
            <p className="text-sm text-gray-400 mb-4">
              Calcule les statistiques pour un mois spécifique.
            </p>
            <div className="flex gap-2 mb-2">
              <select 
                value={selectedMonth} 
                onChange={(e) => setSelectedMonth(Number(e.target.value))}
                className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              >
                {Array.from({length: 12}, (_, i) => i + 1).map(month => (
                  <option key={month} value={month}>
                    {new Date(2025, month - 1).toLocaleString('fr-FR', { month: 'long' })}
                  </option>
                ))}
              </select>
              <select 
                value={selectedYear} 
                onChange={(e) => setSelectedYear(Number(e.target.value))}
                className="w-24 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              >
                {[2025, 2024, 2023, 2022].map(year => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>
            <button
              onClick={handleCalculateMonthlyStats}
              disabled={calculatingMonthlyStats}
              className="btn-secondary w-full flex items-center justify-center gap-2"
            >
              {calculatingMonthlyStats ? (
                <>
                  <ArrowPathIcon className="h-5 w-5 animate-spin" />
                  Calcul en cours...
                </>
              ) : (
                <>
                  <CalendarIcon className="h-5 w-5" />
                  Calculer
                </>
              )}
            </button>
          </div>
        </div>

        {/* Snapshot Results */}
        {snapshotResult && (
          <div className="mb-4 p-4 bg-blue-900/20 border border-blue-500/30 rounded-lg">
            <h4 className="font-semibold text-blue-400 mb-2">✅ Snapshot Créé</h4>
            <p className="text-sm text-gray-300">
              {snapshotResult.snapshots_created} enregistrements créés le{' '}
              {new Date(snapshotResult.timestamp).toLocaleString('fr-FR')}
            </p>
          </div>
        )}

        {/* Stats Results */}
        {statsResult && (
          <div className="mb-4 p-4 bg-purple-900/20 border border-purple-500/30 rounded-lg">
            <h4 className="font-semibold text-purple-400 mb-2">✅ Stats Annuelles Calculées</h4>
            <p className="text-sm text-gray-300">
              {statsResult.users_processed} utilisateurs traités pour l'année {statsResult.year}
            </p>
          </div>
        )}

        {/* Monthly Stats Results */}
        {monthlyStatsResult && (
          <div className="mb-4 p-4 bg-green-900/20 border border-green-500/30 rounded-lg">
            <h4 className="font-semibold text-green-400 mb-2">✅ Stats Mensuelles Calculées</h4>
            <p className="text-sm text-gray-300">
              {monthlyStatsResult.users_processed} utilisateurs traités pour{' '}
              {new Date(monthlyStatsResult.year, monthlyStatsResult.month - 1).toLocaleString('fr-FR', { month: 'long', year: 'numeric' })}
            </p>
          </div>
        )}

        {/* Snapshot History */}
        {snapshotHistory.length > 0 && (
          <div className="border border-gray-700 rounded-lg p-4">
            <h4 className="font-semibold mb-3">Historique des Snapshots</h4>
            <div className="space-y-2">
              {snapshotHistory.map((snap, idx) => (
                <div key={idx} className="flex justify-between items-center text-sm">
                  <span className="text-gray-400">
                    {new Date(snap.date).toLocaleDateString('fr-FR')}
                  </span>
                  <span className="font-mono text-green-400">{snap.snapshots_count} snapshots</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Playtime Tracking Info */}
      <div className="card border border-blue-500/30 bg-blue-900/10">
        <h3 className="font-semibold text-blue-400 mb-2">💡 Comment ça marche ?</h3>
        <ul className="text-sm text-gray-300 space-y-2">
          <li>• <strong>Snapshot :</strong> Enregistre le temps de jeu total actuel de chaque utilisateur/jeu</li>
          <li>• <strong>Stats annuelles :</strong> Compare les snapshots début/fin d'année pour calculer le temps joué</li>
          <li>• <strong>Fréquence recommandée :</strong> 1 snapshot par jour (idéalement à minuit)</li>
          <li>• <strong>Premiers résultats :</strong> Les stats annuelles seront précises après 1 an de tracking</li>
          <li>• <strong>Configuration CRON :</strong> Ajouter une tâche planifiée pour automatiser les snapshots</li>
        </ul>
      </div>
    </div>
  )
}
