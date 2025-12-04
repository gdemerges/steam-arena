import Link from 'next/link'
import { StatsCards } from '@/components/StatsCards'
import { RecentActivity } from '@/components/RecentActivity'

export default function Home() {
  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <Link href="/users/add" className="btn-primary">
          Add Steam User
        </Link>
      </div>
      
      <StatsCards />
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <RecentActivity />
        
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <Link href="/groups/create" className="block p-4 bg-steam-dark rounded hover:bg-gray-700 transition-colors">
              <h3 className="font-semibold text-steam-blue">Create a Group</h3>
              <p className="text-sm text-gray-400">Create a group of Steam friends to compare stats</p>
            </Link>
            <Link href="/compare" className="block p-4 bg-steam-dark rounded hover:bg-gray-700 transition-colors">
              <h3 className="font-semibold text-steam-blue">Compare Users</h3>
              <p className="text-sm text-gray-400">Compare gaming stats between users</p>
            </Link>
            <Link href="/ml/recommendations" className="block p-4 bg-steam-dark rounded hover:bg-gray-700 transition-colors">
              <h3 className="font-semibold text-steam-blue">Get Recommendations</h3>
              <p className="text-sm text-gray-400">Get AI-powered game recommendations</p>
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
