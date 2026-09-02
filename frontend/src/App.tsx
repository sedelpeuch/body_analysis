import { useState } from 'react'
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

const metricCards = [
  { label: 'Poids', value: '75,4 kg', delta: '+0,2 kg', tone: 'body' },
  { label: 'Graisse', value: '17,8 %', delta: '-0,4 %', tone: 'body' },
  { label: 'Calories', value: '2 245', delta: 'objectif 2 300', tone: 'nutrition' },
  { label: 'Entraînement', value: '38 min', delta: '3 séances', tone: 'sport' },
]

const objectiveItems = [
  { label: 'Poids cible', current: '75,4 / 74,0 kg', progress: 68, tone: 'green' },
  { label: 'Masse musculaire', current: '46,1 / 47,0 kg', progress: 82, tone: 'blue' },
  { label: 'Calories moyennes', current: '2 245 / 2 300', progress: 75, tone: 'cyan' },
]

const recentSessions = [
  { name: 'Course légère', value: '32 min', tag: 'Cardio' },
  { name: 'Renforcement', value: '48 min', tag: 'Muscu' },
  { name: 'Natation', value: '28 min', tag: 'Endurance' },
]

const photoHighlights = [
  { tag: 'Face', date: '12 juin', status: 'Confidentiel' },
  { tag: 'Profil', date: '09 juin', status: 'Visible' },
  { tag: 'Bras', date: '07 juin', status: 'Visible' },
]

function App() {
  const [activeTab, setActiveTab] = useState<NavItem>('Aujourd’hui')

  const renderContent = () => {
    switch (activeTab) {
      case 'Corps':
        return (
          <section className="section-grid">
            <article className="panel large-panel">
              <div className="panel-header">
                <h3>Évolution du poids</h3>
                <span>30 jours</span>
              </div>
              <div className="chart-surface">
                <div className="chart-grid" aria-hidden="true">
                  {[...Array(6)].map((_, index) => (
                    <span key={index} />
                  ))}
                </div>
                <div className="line-chart" />
              </div>
            </article>

            <article className="panel">
              <div className="panel-header">
                <h3>Masse</h3>
                <span>kg</span>
              </div>
              <ul className="stat-list">
                <li><span>Graisse</span><strong>17,8%</strong></li>
                <li><span>Muscle</span><strong>46,1 kg</strong></li>
                <li><span>Eau</span><strong>42,6 kg</strong></li>
              </ul>
            </article>
          </section>
        )
      case 'Nutrition':
        return (
          <section className="section-grid">
            <article className="panel large-panel">
              <div className="panel-header">
                <h3>Calories journalières</h3>
                <span>7 jours</span>
              </div>
              <div className="bar-stack" aria-label="Calories par jour">
                {[66, 77, 58, 84, 71, 90, 60].map((height, index) => (
                  <span key={index} style={{ height: `${height}%` }} />
                ))}
              </div>
            </article>

            <article className="panel">
              <div className="panel-header">
                <h3>Repas</h3>
                <span>répartition</span>
              </div>
              <ul className="stat-list">
                <li><span>Petit-déj</span><strong>512 kcal</strong></li>
                <li><span>Déjeuner</span><strong>698 kcal</strong></li>
                <li><span>Dîner</span><strong>820 kcal</strong></li>
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
                <span>8 périodes</span>
              </div>
              <div className="timeline">
                <div><span>Janv.</span><strong>Bulk</strong></div>
                <div><span>Mars</span><strong>Cut</strong></div>
                <div><span>Juin</span><strong>Cut</strong></div>
                <div><span>Août</span><strong>Maintien</strong></div>
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
                <li><span>Export Samsung</span><strong>Prêt</strong></li>
                <li><span>MinIO</span><strong>85 photos</strong></li>
                <li><span>Base</span><strong>PostgreSQL</strong></li>
              </ul>
            </article>
            <article className="panel">
              <div className="panel-header">
                <h3>Dernière synchronisation</h3>
                <span>08:40</span>
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
                <span className="status-pill ok">En ligne</span>
              </div>

              <div className="summary-row">
                <div>
                  <p className="metric-label">Variation 30 jours</p>
                  <h3>-1,2 kg</h3>
                </div>

                <div className="ring-chart" style={{ ['--progress' as string]: '68%' }}>
                  <span>68%</span>
                </div>
              </div>

              <p className="muted-line">
                Progression vers la cible de phase : 5,2 kg restant sur le plan actuel.
              </p>
            </div>

            <div className="hero-card impact-card">
              <div className="card-header">
                <span className="chip chip-sport">Entraînement</span>
              </div>
              <ul className="mini-list">
                {recentSessions.map((entry) => (
                  <li key={entry.name}>
                    <span>{entry.name}</span>
                    <strong>{entry.value}</strong>
                    <em>{entry.tag}</em>
                  </li>
                ))}
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
            <h2>Sèche — 7 semaines</h2>
          </div>
          <button type="button" className="topbar-button">
            Importer des données
          </button>
        </header>

        {activeTab === 'Aujourd’hui' && (
          <>
            <section className="hero-grid">
              <div className="hero-card summary-card">
                <div className="card-header">
                  <span className="chip chip-body">Corps</span>
                  <span className="status-pill ok">En ligne</span>
                </div>

                <div className="summary-row">
                  <div>
                    <p className="metric-label">Variation 30 jours</p>
                    <h3>-1,2 kg</h3>
                  </div>

                  <div className="ring-chart" style={{ ['--progress' as string]: '68%' }}>
                    <span>68%</span>
                  </div>
                </div>

                <p className="muted-line">
                  Progression vers la cible de phase : 5,2 kg restant sur le plan actuel.
                </p>
              </div>

              <div className="hero-card impact-card">
                <div className="card-header">
                  <span className="chip chip-sport">Entraînement</span>
                </div>
                <ul className="mini-list">
                  {recentSessions.map((entry) => (
                    <li key={entry.name}>
                      <span>{entry.name}</span>
                      <strong>{entry.value}</strong>
                      <em>{entry.tag}</em>
                    </li>
                  ))}
                </ul>
              </div>
            </section>

            <section className="metrics-grid">
              {metricCards.map((card) => (
                <article key={card.label} className={`metric-card tone-${card.tone}`}>
                  <p>{card.label}</p>
                  <h3>{card.value}</h3>
                  <span>{card.delta}</span>
                </article>
              ))}
            </section>

            <section className="content-grid">
              <article className="panel">
                <div className="panel-header">
                  <h3>Objectifs de phase</h3>
                  <span>3 actifs</span>
                </div>
                <div className="objective-list">
                  {objectiveItems.map((item) => (
                    <div key={item.label} className="objective-item">
                      <div className="objective-topline">
                        <span>{item.label}</span>
                        <strong>{item.current}</strong>
                      </div>
                      <div className="progress-track">
                        <div
                          className={`progress-fill ${item.tone}`}
                          style={{ width: `${item.progress}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </article>

              <article className="panel">
                <div className="panel-header">
                  <h3>Photos récentes</h3>
                  <span>21 dates</span>
                </div>
                <div className="photo-grid">
                  {photoHighlights.map((photo) => (
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
