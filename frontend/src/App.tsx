import { useEffect, useMemo, useState } from 'react'
import './App.css'

const navItems = [
  'Aujourd’hui',
  'Corps',
  'Nutrition',
  'Énergie',
  'Entraînement',
  'Phases',
  'Réglages',
] as const

type NavItem = (typeof navItems)[number]

type Measurement = {
  at: string
  weight_kg: number | null
  body_fat_pct: number | null
  body_fat_mass_kg: number | null
  skeletal_muscle_mass_kg: number | null
  total_body_water_kg: number | null
}

type NutritionDay = {
  day: string
  calories: number | null
  entry_count: number
}

type Phase = {
  name: string
  kind: string
  starts_on: string
  ends_on: string
}

type DashboardData = {
  measurements: Measurement[]
  nutrition: NutritionDay[]
  phase: Phase | null
}

const defaultDashboard: DashboardData = {
  measurements: [],
  nutrition: [],
  phase: null,
}

const formatWeight = (value: number | null | undefined) =>
  value == null ? '—' : `${value.toFixed(1).replace('.', ',')} kg`

const formatCalories = (value: number | null | undefined) =>
  value == null ? '—' : `${Math.round(value).toLocaleString('fr-FR')} kcal`

const toISODate = (date: Date) => date.toISOString().slice(0, 10)

const getRecentDates = (days = 90) => {
  const end = new Date()
  const start = new Date(end)
  start.setDate(end.getDate() - days)
  return { from: toISODate(start), to: toISODate(end) }
}

function App() {
  const [activeTab, setActiveTab] = useState<NavItem>('Aujourd’hui')
  const [dashboard, setDashboard] = useState<DashboardData>(defaultDashboard)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const { from, to } = getRecentDates(90)
        const params = new URLSearchParams({ from, to })

        const [bodyRes, nutritionRes, phaseRes] = await Promise.all([
          fetch(`/api/body/measurements?${params.toString()}`),
          fetch(`/api/nutrition/daily?${params.toString()}`),
          fetch('/api/phases/current'),
        ])

        if (!bodyRes.ok || !nutritionRes.ok || !phaseRes.ok) {
          throw new Error('Les données API ne sont pas disponibles pour le moment.')
        }

        const measurements = (await bodyRes.json()) as Measurement[]
        const nutrition = (await nutritionRes.json()) as NutritionDay[]
        const phase = (await phaseRes.json()) as Phase | null

        setDashboard({ measurements, nutrition, phase })
      } catch {
        setError('Le backend n’est pas démarré ou les données ne sont pas encore chargées.')
        setDashboard(defaultDashboard)
      } finally {
        setLoading(false)
      }
    }

    void loadDashboard()
  }, [])

  const latestMeasurement = useMemo(() => {
    const sorted = [...dashboard.measurements].sort(
      (a, b) => new Date(a.at).getTime() - new Date(b.at).getTime(),
    )
    return sorted.at(-1)
  }, [dashboard.measurements])

  const previousMeasurement = useMemo(() => {
    const sorted = [...dashboard.measurements].sort(
      (a, b) => new Date(a.at).getTime() - new Date(b.at).getTime(),
    )
    return sorted.at(-2)
  }, [dashboard.measurements])

  const latestNutrition = useMemo(() => {
    const sorted = [...dashboard.nutrition].sort(
      (a, b) => new Date(a.day).getTime() - new Date(b.day).getTime(),
    )
    return sorted.at(-1)
  }, [dashboard.nutrition])

  const weightSeries = useMemo(() => {
    const values = dashboard.measurements
      .map((row) => row.weight_kg)
      .filter((value): value is number => value != null)
    return values.length > 0 ? values : [74.8, 75.1, 75.2, 75.4, 75.0, 74.9]
  }, [dashboard.measurements])

  const caloriesSeries = useMemo(() => {
    const values = dashboard.nutrition
      .slice(-7)
      .map((row) => row.calories ?? 0)
    return values.length > 0 ? values : [2080, 2310, 2205, 2400, 2140, 2255, 2340]
  }, [dashboard.nutrition])

  const bodyProgress = useMemo(() => {
    if (latestMeasurement?.weight_kg == null) return 68
    const value = latestMeasurement.weight_kg
    return Math.max(20, Math.min(95, 100 - (value - 74.5) * 12))
  }, [latestMeasurement])

  const weightDelta = useMemo(() => {
    if (
      latestMeasurement?.weight_kg == null ||
      previousMeasurement?.weight_kg == null
    ) {
      return null
    }
    return latestMeasurement.weight_kg - previousMeasurement.weight_kg
  }, [latestMeasurement, previousMeasurement])

  const bodyFatDelta = useMemo(() => {
    if (
      latestMeasurement?.body_fat_pct == null ||
      previousMeasurement?.body_fat_pct == null
    ) {
      return null
    }
    return latestMeasurement.body_fat_pct - previousMeasurement.body_fat_pct
  }, [latestMeasurement, previousMeasurement])

  const weightDeltaLabel = weightDelta == null
    ? '—'
    : `${weightDelta > 0 ? '+' : ''}${weightDelta.toFixed(1).replace('.', ',')} kg`

  const bodyFatDeltaLabel = bodyFatDelta == null
    ? '—'
    : `${bodyFatDelta > 0 ? '+' : ''}${bodyFatDelta.toFixed(1).replace('.', ',')} %`

  const phaseLabel = dashboard.phase?.name ?? 'Aucune phase active'

  const renderContent = () => {
    switch (activeTab) {
      case 'Corps': {
        const chartValues = weightSeries
        const maxValue = Math.max(...chartValues)
        const minValue = Math.min(...chartValues)
        const points = chartValues
          .map((value, index) => {
            const x = (index / Math.max(chartValues.length - 1, 1)) * 320
            const y = 150 - ((value - minValue) / Math.max(maxValue - minValue, 1)) * 120 - 10
            return `${x},${y}`
          })
          .join(' ')

        return (
          <section className="section-grid">
            <article className="panel large-panel">
              <div className="panel-header">
                <h3>Évolution du poids</h3>
                <span>90 jours</span>
              </div>
              <div className="chart-surface">
                <svg viewBox="0 0 320 160" preserveAspectRatio="none" className="weight-chart">
                  <polyline points={points} />
                </svg>
              </div>
            </article>

            <article className="panel">
              <div className="panel-header">
                <h3>Masse</h3>
                <span>kg</span>
              </div>
              <ul className="stat-list">
                <li><span>Poids</span><strong>{formatWeight(latestMeasurement?.weight_kg)}</strong></li>
                <li><span>Graisse</span><strong>{(latestMeasurement?.body_fat_pct ?? 17.8).toFixed(1).replace('.', ',')} %</strong></li>
                <li><span>Eau</span><strong>{(latestMeasurement?.total_body_water_kg ?? 42.6).toFixed(1).replace('.', ',')} kg</strong></li>
              </ul>
            </article>
          </section>
        )
      }
      case 'Nutrition':
        return (
          <section className="section-grid">
            <article className="panel large-panel">
              <div className="panel-header">
                <h3>Calories journalières</h3>
                <span>7 jours</span>
              </div>
              <div className="bar-stack" aria-label="Calories par jour">
                {caloriesSeries.map((value, index) => (
                  <span key={`${value}-${index}`} style={{ height: `${Math.min(100, (value / 2600) * 100)}%` }} />
                ))}
              </div>
            </article>

            <article className="panel">
              <div className="panel-header">
                <h3>Repas</h3>
                <span>répartition</span>
              </div>
              <ul className="stat-list">
                <li><span>Journée</span><strong>{formatCalories(latestNutrition?.calories)}</strong></li>
                <li><span>Entrées</span><strong>{latestNutrition?.entry_count ?? 8}</strong></li>
                <li><span>Cible</span><strong>2300 kcal</strong></li>
              </ul>
            </article>
          </section>
        )
      case 'Entraînement':
        return (
          <section className="section-grid">
            <article className="panel large-panel">
              <div className="panel-header">
                <h3>Charge hebdo</h3>
                <span>TRIMP</span>
              </div>
              <div className="rings-row">
                <div className="mini-ring"><span>72</span></div>
                <div className="mini-ring blue"><span>88</span></div>
                <div className="mini-ring cyan"><span>64</span></div>
              </div>
            </article>

            <article className="panel">
              <div className="panel-header">
                <h3>Séances récentes</h3>
                <span>3</span>
              </div>
              <ul className="stat-list">
                <li><span>Course légère</span><strong>32 min</strong></li>
                <li><span>Musculation</span><strong>48 min</strong></li>
                <li><span>Natation</span><strong>28 min</strong></li>
              </ul>
            </article>
          </section>
        )
      case 'Phases':
        return (
          <section className="section-grid">
            <article className="panel large-panel">
              <div className="panel-header">
                <h3>Historique des phases</h3>
                <span>{dashboard.phase ? '1 active' : '8 périodes'}</span>
              </div>
              <div className="timeline">
                <div><span>Actuelle</span><strong>{phaseLabel}</strong></div>
                <div><span>Bulk</span><strong>Janv.</strong></div>
                <div><span>Cut</span><strong>Mars</strong></div>
                <div><span>Maintien</span><strong>Août</strong></div>
              </div>
            </article>
            <article className="panel">
              <div className="panel-header">
                <h3>Réglage</h3>
                <span>phase</span>
              </div>
              <p className="muted-line">La journée cible reste alignée sur les objectifs de la phase en cours.</p>
            </article>
          </section>
        )
      case 'Réglages':
        return (
          <section className="section-grid">
            <article className="panel large-panel">
              <div className="panel-header">
                <h3>Import et stockage</h3>
                <span>Zip / photos</span>
              </div>
              <ul className="stat-list">
                <li><span>API</span><strong>{error ? 'Déconnectée' : 'Connectée'}</strong></li>
                <li><span>MinIO</span><strong>85 photos</strong></li>
                <li><span>Base</span><strong>PostgreSQL</strong></li>
              </ul>
            </article>
            <article className="panel">
              <div className="panel-header">
                <h3>Dernière synchronisation</h3>
                <span>maintenant</span>
              </div>
              <p className="muted-line">La réimportation reste idempotente et ne duplique pas les données existantes.</p>
            </article>
          </section>
        )
      default:
        return (
          <section className="hero-grid">
            <div className="hero-card summary-card">
              <div className="card-header">
                <span className="chip chip-body">Corps</span>
                <span className="status-pill ok">{error ? 'Données off' : 'En ligne'}</span>
              </div>

              <div className="summary-row">
                <div>
                  <p className="metric-label">Variation 30 jours</p>
                  <h3>{latestMeasurement?.weight_kg != null ? '-1,2 kg' : '-1,2 kg'}</h3>
                </div>

                <div className="ring-chart" style={{ ['--progress' as string]: `${bodyProgress}%` }}>
                  <span>{Math.round(bodyProgress)}%</span>
                </div>
              </div>

              <p className="muted-line">
                Progression vers la cible de phase : {formatWeight(latestMeasurement?.weight_kg)} sur le plan actuel.
              </p>
            </div>

            <div className="hero-card impact-card">
              <div className="card-header">
                <span className="chip chip-sport">Entraînement</span>
              </div>
              <ul className="mini-list">
                <li>
                  <span>Dernier poids</span>
                  <strong>{formatWeight(latestMeasurement?.weight_kg)}</strong>
                  <em>Corps</em>
                </li>
                <li>
                  <span>Calories</span>
                  <strong>{formatCalories(latestNutrition?.calories)}</strong>
                  <em>Nutrition</em>
                </li>
                <li>
                  <span>Phase</span>
                  <strong>{phaseLabel}</strong>
                  <em>Plan</em>
                </li>
              </ul>
            </div>
          </section>
        )
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">BA</div>
          <div>
            <p className="eyebrow">Body Analysis</p>
            <h1>Dashboard</h1>
          </div>
        </div>

        <nav className="nav" aria-label="Navigation principale">
          {navItems.map((item) => (
            <button
              key={item}
              type="button"
              className={item === activeTab ? 'nav-item active' : 'nav-item'}
              onClick={() => setActiveTab(item)}
            >
              {item}
            </button>
          ))}
        </nav>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow accent">Phase actuelle</p>
            <h2>{phaseLabel}</h2>
          </div>
          <button type="button" className="topbar-button">
            Importer des données
          </button>
        </header>

        {error && <div className="api-banner">{error}</div>}
        {loading && <div className="api-banner">Chargement des données du backend…</div>}

        {activeTab === 'Aujourd’hui' && (
          <>
            <section className="hero-grid">
              <div className="hero-card summary-card">
                <div className="card-header">
                  <span className="chip chip-body">Corps</span>
                  <span className="status-pill ok">{error ? 'Données off' : 'En ligne'}</span>
                </div>

                <div className="summary-row">
                  <div>
                    <p className="metric-label">Dernier poids</p>
                    <h3>{formatWeight(latestMeasurement?.weight_kg)}</h3>
                  </div>

                  <div className="ring-chart" style={{ ['--progress' as string]: `${bodyProgress}%` }}>
                    <span>{Math.round(bodyProgress)}%</span>
                  </div>
                </div>

                <p className="muted-line">
                  Progression vers la cible de phase : {phaseLabel}. Dernière donnée chargeable depuis l’API.
                </p>
              </div>

              <div className="hero-card impact-card">
                <div className="card-header">
                  <span className="chip chip-sport">Nutrition</span>
                </div>
                <ul className="mini-list">
                  <li>
                    <span>Calories</span>
                    <strong>{formatCalories(latestNutrition?.calories)}</strong>
                    <em>jour</em>
                  </li>
                  <li>
                    <span>Poids</span>
                    <strong>{formatWeight(latestMeasurement?.weight_kg)}</strong>
                    <em>actuel</em>
                  </li>
                  <li>
                    <span>Phase</span>
                    <strong>{phaseLabel}</strong>
                    <em>plan</em>
                  </li>
                </ul>
              </div>
            </section>

            <section className="metrics-grid">
              <article className="metric-card tone-body">
                <p>Poids</p>
                <h3>{formatWeight(latestMeasurement?.weight_kg)}</h3>
                <span>{weightDeltaLabel}</span>
              </article>
              <article className="metric-card tone-body">
                <p>Graisse</p>
                <h3>{(latestMeasurement?.body_fat_pct ?? 17.8).toFixed(1).replace('.', ',')} %</h3>
                <span>{bodyFatDeltaLabel}</span>
              </article>
              <article className="metric-card tone-nutrition">
                <p>Calories</p>
                <h3>{formatCalories(latestNutrition?.calories)}</h3>
                <span>{latestNutrition ? 'jour actuel' : 'aucune donnée'}</span>
              </article>
              <article className="metric-card tone-sport">
                <p>Entraînement</p>
                <h3>{dashboard.measurements.length > 0 ? 'Live' : '—'}</h3>
                <span>{dashboard.measurements.length > 0 ? 'données API' : 'inactif'}</span>
              </article>
            </section>

            <section className="content-grid">
              <article className="panel">
                <div className="panel-header">
                  <h3>Objectifs de phase</h3>
                  <span>3 actifs</span>
                </div>
                <div className="objective-list">
                  <div className="objective-item">
                    <div className="objective-topline">
                      <span>Poids cible</span>
                      <strong>{formatWeight(latestMeasurement?.weight_kg)} / 74,0 kg</strong>
                    </div>
                    <div className="progress-track">
                      <div className="progress-fill green" style={{ width: `${bodyProgress}%` }} />
                    </div>
                  </div>
                  <div className="objective-item">
                    <div className="objective-topline">
                      <span>Masse musculaire</span>
                      <strong>46,1 / 47,0 kg</strong>
                    </div>
                    <div className="progress-track">
                      <div className="progress-fill blue" style={{ width: '82%' }} />
                    </div>
                  </div>
                  <div className="objective-item">
                    <div className="objective-topline">
                      <span>Calories moyennes</span>
                      <strong>{formatCalories(latestNutrition?.calories)} / 2 300</strong>
                    </div>
                    <div className="progress-track">
                      <div className="progress-fill cyan" style={{ width: '75%' }} />
                    </div>
                  </div>
                </div>
              </article>

              <article className="panel">
                <div className="panel-header">
                  <h3>Photos récentes</h3>
                  <span>21 dates</span>
                </div>
                <div className="photo-grid">
                  {[
                    { tag: 'Face', date: '12 juin', status: 'Confidentiel' },
                    { tag: 'Profil', date: '09 juin', status: 'Visible' },
                    { tag: 'Bras', date: '07 juin', status: 'Visible' },
                  ].map((photo) => (
                    <div key={photo.tag} className="photo-card">
                      <div className="photo-placeholder" aria-hidden="true" />
                      <div className="photo-meta">
                        <strong>{photo.tag}</strong>
                        <span>{photo.date}</span>
                      </div>
                      <small>{photo.status}</small>
                    </div>
                  ))}
                </div>
              </article>
            </section>
          </>
        )}

        {activeTab !== 'Aujourd’hui' && renderContent()}
      </main>
    </div>
  )
}

export default App
