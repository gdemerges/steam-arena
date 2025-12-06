'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  extractAllFeatures,
  clusterPlayers,
  getClusters,
  getFeatureStats,
  exportDataset,
} from '@/lib/api'
import {
  CpuChipIcon,
  ArrowPathIcon,
  ArrowDownTrayIcon,
  SparklesIcon,
  ChartPieIcon,
} from '@heroicons/react/24/outline'
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'

interface ClusterData {
  cluster_id: number
  member_count: number
  avg_playtime: number
  avg_games: number
  avg_achievements: number
  avg_completion_rate: number
  dominant_genre: string
}

interface FeatureStats {
  total_users_with_features: number
  clustered_users: number
  averages: {
    games_per_user: number
    playtime_hours: number
    completion_rate: number
    genre_diversity: number
  }
  top_favorite_genres: Array<{ genre: string; count: number }>
}

const COLORS = ['#66C0F4', '#4ade80', '#a855f7', '#fb923c', '#f43f5e', '#06b6d4', '#eab308', '#ec4899']

export default function MLPage() {
  const [clusters, setClusters] = useState<ClusterData[]>([])
  const [featureStats, setFeatureStats] = useState<FeatureStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [extracting, setExtracting] = useState(false)
  const [clustering, setClustering] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [nClusters, setNClusters] = useState(5)

  const loadData = async () => {
    setLoading(true)
    try {
      const [clustersRes, statsRes] = await Promise.all([
        getClusters().catch(() => ({ data: [] })),
        getFeatureStats().catch(() => ({ data: null })),
      ])
      // Handle case where API returns an object instead of array
      setClusters(Array.isArray(clustersRes.data) ? clustersRes.data : [])
      setFeatureStats(statsRes.data)
    } catch (error) {
      console.error('Failed to load ML data:', error)
      setClusters([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleExtractFeatures = async () => {
    setExtracting(true)
    try {
      await extractAllFeatures()
      await loadData()
      alert('Features extracted successfully!')
    } catch (error) {
      console.error('Feature extraction failed:', error)
      alert('Feature extraction failed. Make sure you have users with games in the database.')
    } finally {
      setExtracting(false)
    }
  }

  const handleCluster = async () => {
    setClustering(true)
    try {
      if (!featureStats || featureStats.total_users_with_features === 0) {
        alert('No users with features yet. Please extract features first.')
        setClustering(false)
        return
      }
      if (featureStats.total_users_with_features < nClusters) {
        alert(`Not enough users (${featureStats.total_users_with_features}) for ${nClusters} clusters. Reduce the number of clusters.`)
        setClustering(false)
        return
      }
      await clusterPlayers(nClusters)
      await loadData()
      alert('Clustering completed!')
    } catch (error) {
      console.error('Clustering failed:', error)
      alert('Clustering failed: ' + (error instanceof Error ? error.message : 'Unknown error'))
    } finally {
      setClustering(false)
    }
  }

  const handleExport = async (format: 'json' | 'csv') => {
    setExporting(true)
    try {
      const res = await exportDataset(format)
      const blob = new Blob([res.data], {
        type: format === 'json' ? 'application/json' : 'text/csv'
      })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `steam_ml_dataset.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Export failed:', error)
      alert('Export failed')
    } finally {
      setExporting(false)
    }
  }

  // Prepare chart data
  const clusterPieData = clusters.map(c => ({
    name: `Cluster ${c.cluster_id}`,
    value: c.member_count,
  }))

  const clusterScatterData = clusters.map(c => ({
    x: c.avg_games,
    y: c.avg_playtime / 60,
    z: c.member_count * 100,
    cluster: c.cluster_id,
    genre: c.dominant_genre,
  }))

  const genreData = featureStats?.top_favorite_genres
    ? featureStats.top_favorite_genres
        .slice(0, 8)
        .map(g => ({ name: g.genre, value: g.count }))
    : []

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">ML Analytics</h1>
        <Link href="/ml/recommendations" className="btn-primary flex items-center gap-2">
          <SparklesIcon className="h-5 w-5" />
          Recommendations
        </Link>
      </div>

      {/* Instructions */}
      <div className="card border border-steam-blue/30 bg-steam-blue/5">
        <p className="text-sm text-gray-300">
          <span className="font-semibold text-steam-blue">ML Analytics Workflow:</span>
        </p>
        <ol className="text-sm text-gray-400 mt-2 ml-4 space-y-1">
          <li>1. <strong>Extract Features</strong> - Analyze all users to calculate ML features</li>
          <li>2. <strong>Cluster Players</strong> - Group users based on their behavior patterns</li>
          <li>3. <strong>Export Dataset</strong> - Download the data for external analysis</li>
        </ol>
        {featureStats && featureStats.total_users_with_features === 0 && (
          <p className="text-sm text-yellow-400 mt-3">⚠️ No users with features yet. Start by clicking "Extract Features".</p>
        )}
      </div>

      {/* Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <h3 className="font-semibold mb-3">1. Extract Features</h3>
          <p className="text-sm text-gray-400 mb-4">
            Calculate ML features (playtime, completion rate, etc.) for all users
          </p>
          <button
            onClick={handleExtractFeatures}
            disabled={extracting}
            className="btn-secondary w-full flex items-center justify-center gap-2"
          >
            {extracting ? (
              <>
                <ArrowPathIcon className="h-5 w-5 animate-spin" />
                Extracting...
              </>
            ) : (
              <>
                <CpuChipIcon className="h-5 w-5" />
                Extract Features
              </>
            )}
          </button>
        </div>

        <div className="card">
          <h3 className="font-semibold mb-3">2. Cluster Players</h3>
          <p className="text-sm text-gray-400 mb-2">
            Group players into clusters based on behavior
          </p>
          <div className="flex items-center gap-2 mb-4">
            <label className="text-sm text-gray-400">Clusters:</label>
            <input
              type="number"
              min={2}
              max={10}
              value={nClusters}
              onChange={(e) => setNClusters(parseInt(e.target.value) || 5)}
              className="input w-20"
            />
          </div>
          <button
            onClick={handleCluster}
            disabled={clustering}
            className="btn-secondary w-full flex items-center justify-center gap-2"
          >
            {clustering ? (
              <>
                <ArrowPathIcon className="h-5 w-5 animate-spin" />
                Clustering...
              </>
            ) : (
              <>
                <ChartPieIcon className="h-5 w-5" />
                Run Clustering
              </>
            )}
          </button>
        </div>

        <div className="card">
          <h3 className="font-semibold mb-3">3. Export Dataset</h3>
          <p className="text-sm text-gray-400 mb-4">
            Download features for external ML analysis
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => handleExport('json')}
              disabled={exporting}
              className="btn-secondary flex-1 flex items-center justify-center gap-2"
            >
              <ArrowDownTrayIcon className="h-5 w-5" />
              JSON
            </button>
            <button
              onClick={() => handleExport('csv')}
              disabled={exporting}
              className="btn-secondary flex-1 flex items-center justify-center gap-2"
            >
              <ArrowDownTrayIcon className="h-5 w-5" />
              CSV
            </button>
          </div>
        </div>
      </div>

      {/* Stats Overview */}
      {featureStats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="card text-center">
            <p className="text-2xl font-bold text-steam-blue">{featureStats.total_users_with_features}</p>
            <p className="text-sm text-gray-400">Users with Features</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-purple-400">
              {Math.round(featureStats.averages.games_per_user)}
            </p>
            <p className="text-sm text-gray-400">Avg Games</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-yellow-400">
              {Math.round(featureStats.averages.playtime_hours)}h
            </p>
            <p className="text-sm text-gray-400">Avg Playtime</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-green-400">
              {(featureStats.averages.completion_rate * 100).toFixed(1)}%
            </p>
            <p className="text-sm text-gray-400">Avg Achievement Rate</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-orange-400">
              {(featureStats.averages.completion_rate * 100).toFixed(1)}%
            </p>
            <p className="text-sm text-gray-400">Avg Completion</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cluster Distribution */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Cluster Distribution</h2>
          {clusters.length === 0 ? (
            <p className="text-gray-400 text-center py-12">
              No clusters yet. Run clustering first.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={clusterPieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                >
                  {clusterPieData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#1a1a2e', border: 'none', borderRadius: '8px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Genre Distribution */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Genre Distribution</h2>
          {genreData.length === 0 ? (
            <p className="text-gray-400 text-center py-12">
              No genre data available. Extract features first.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={genreData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ name }) => name}
                >
                  {genreData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#1a1a2e', border: 'none', borderRadius: '8px' }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Cluster Scatter Plot */}
      {clusters.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Cluster Visualization (Games vs Playtime)</h2>
          <ResponsiveContainer width="100%" height={400}>
            <ScatterChart>
              <XAxis
                dataKey="x"
                name="Games"
                tick={{ fill: '#9ca3af' }}
                label={{ value: 'Avg Games', position: 'bottom', fill: '#9ca3af' }}
              />
              <YAxis
                dataKey="y"
                name="Playtime"
                tick={{ fill: '#9ca3af' }}
                label={{ value: 'Avg Playtime (h)', angle: -90, position: 'left', fill: '#9ca3af' }}
              />
              <ZAxis dataKey="z" range={[100, 1000]} />
              <Tooltip
                contentStyle={{ background: '#1a1a2e', border: 'none', borderRadius: '8px' }}
                formatter={(value: number, name: string) => {
                  if (name === 'x') return [`${value} games`, 'Avg Games']
                  if (name === 'y') return [`${value.toFixed(0)}h`, 'Avg Playtime']
                  return [value, name]
                }}
              />
              <Scatter data={clusterScatterData} fill="#66C0F4">
                {clusterScatterData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Cluster Details Table */}
      {clusters.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Cluster Details</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-700">
                  <th className="pb-3 font-medium">Cluster</th>
                  <th className="pb-3 font-medium text-right">Members</th>
                  <th className="pb-3 font-medium text-right">Avg Games</th>
                  <th className="pb-3 font-medium text-right">Avg Playtime</th>
                  <th className="pb-3 font-medium text-right">Avg Achievements</th>
                  <th className="pb-3 font-medium text-right">Completion</th>
                  <th className="pb-3 font-medium">Top Genre</th>
                </tr>
              </thead>
              <tbody>
                {clusters.map((cluster, index) => (
                  <tr key={cluster.cluster_id} className="border-b border-gray-700/50">
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-4 h-4 rounded-full"
                          style={{ backgroundColor: COLORS[index % COLORS.length] }}
                        />
                        Cluster {cluster.cluster_id}
                      </div>
                    </td>
                    <td className="py-3 text-right">{cluster.member_count}</td>
                    <td className="py-3 text-right">{Math.round(cluster.avg_games)}</td>
                    <td className="py-3 text-right">{Math.round(cluster.avg_playtime / 60)}h</td>
                    <td className="py-3 text-right">{Math.round(cluster.avg_achievements)}</td>
                    <td className="py-3 text-right">{(cluster.avg_completion_rate * 100).toFixed(1)}%</td>
                    <td className="py-3">{cluster.dominant_genre || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
