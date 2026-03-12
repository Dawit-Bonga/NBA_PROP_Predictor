import { FormEvent, useEffect, useState } from "react";
import { api } from "./api";
import type {
  ApiConfig,
  BetRow,
  HealthResponse,
  ModelsResponse,
  PlayerInsightsResponse,
  PredictionResponse,
  PredictionRow,
  PropRow,
  Target,
} from "./types";

const TEAM_OPTIONS = [
  "ATL", "BKN", "BOS", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW",
  "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK",
  "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS",
];

const DEFAULT_LINES: Record<Target, number> = { PTS: 20.5, REB: 5.5, AST: 4.5 };

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [config, setConfig] = useState<ApiConfig | null>(null);
  const [players, setPlayers] = useState<string[]>([]);
  const [models, setModels] = useState<ModelsResponse>({});
  const [props, setProps] = useState<PropRow[]>([]);
  const [analysisRows, setAnalysisRows] = useState<PredictionRow[]>([]);
  const [rankedBets, setRankedBets] = useState<BetRow[]>([]);
  const [selectedPlayer, setSelectedPlayer] = useState("LeBron James");
  const [useAutoContext, setUseAutoContext] = useState(true);
  const [opponent, setOpponent] = useState("BOS");
  const [isHome, setIsHome] = useState<0 | 1>(1);
  const [restDays, setRestDays] = useState(1);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [insights, setInsights] = useState<PlayerInsightsResponse | null>(null);
  const [lines, setLines] = useState(DEFAULT_LINES);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshingBoard, setRefreshingBoard] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      try {
        const [
          healthData,
          configData,
          playerData,
          modelData,
          propsData,
          predictionsData,
          betsData,
        ] = await Promise.all([
          api.health(),
          api.config(),
          api.players(),
          api.models(),
          api.props(),
          api.predictions(),
          api.bets(),
        ]);
        if (cancelled) {
          return;
        }
        setHealth(healthData);
        setConfig(configData);
        setPlayers(playerData.players);
        setModels(modelData);
        setProps(propsData.props);
        setAnalysisRows(predictionsData.predictions);
        setRankedBets(betsData.bets);
        if (!playerData.players.includes("LeBron James") && playerData.players[0]) {
          setSelectedPlayer(playerData.players[0]);
        }
      } catch (bootstrapError) {
        if (!cancelled) {
          setError(bootstrapError instanceof Error ? bootstrapError.message : "Failed to load frontend data.");
        }
      }
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = useAutoContext
        ? { player: selectedPlayer }
        : { player: selectedPlayer, opponent, is_home: isHome, rest_days: restDays };
      const [predictionResponse, insightsResponse] = await Promise.all([
        api.predict(payload),
        api.playerInsights(payload),
      ]);
      setPrediction(predictionResponse);
      setInsights(insightsResponse);
    } catch (submitError) {
      setPrediction(null);
      setInsights(null);
      setError(submitError instanceof Error ? submitError.message : "Prediction failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRefreshBoard() {
    setRefreshingBoard(true);
    setError(null);
    try {
      await api.refreshPipeline(2);
      const [predictionsData, betsData] = await Promise.all([api.predictions(), api.bets()]);
      setAnalysisRows(predictionsData.predictions);
      setRankedBets(betsData.bets);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Failed to refresh board predictions.");
    } finally {
      setRefreshingBoard(false);
    }
  }

  const targets = config?.targets ?? ["PTS", "REB", "AST"];

  return (
    <div className="page-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />

      <header className="hero">
        <section>
          <p className="eyebrow">React Migration</p>
          <h1>NBA Prop Predictor frontend scaffold</h1>
          <p className="hero-copy">
            This client talks to the FastAPI backend and now covers single-player predictions,
            the current prop board, and ranked bet outputs without embedding model logic in the UI.
          </p>
        </section>
        <section className="hero-status">
          <div className="status-card">
            <span>API status</span>
            <strong>{health?.status ?? "loading"}</strong>
          </div>
          <div className="status-card">
            <span>Targets</span>
            <strong>{targets.join(" / ")}</strong>
          </div>
          <div className="status-card">
            <span>Endpoint</span>
            <strong>{api.baseUrl}</strong>
          </div>
        </section>
      </header>

      <main className="content-grid">
        <section className="panel form-panel">
          <div className="panel-header">
            <p className="eyebrow">Query</p>
            <h2>Prediction input</h2>
          </div>
          <form className="prediction-form" onSubmit={handleSubmit}>
            <label>
              Player
              <select value={selectedPlayer} onChange={(event) => setSelectedPlayer(event.target.value)}>
                {players.map((player) => (
                  <option key={player} value={player}>
                    {player}
                  </option>
                ))}
              </select>
            </label>

            <label className="toggle-row">
              <span>Infer today&apos;s matchup automatically</span>
              <input
                type="checkbox"
                checked={useAutoContext}
                onChange={(event) => setUseAutoContext(event.target.checked)}
              />
            </label>

            <div className="grid-two">
              <label>
                Opponent
                <select disabled={useAutoContext} value={opponent} onChange={(event) => setOpponent(event.target.value)}>
                  {TEAM_OPTIONS.map((team) => (
                    <option key={team} value={team}>
                      {team}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Location
                <select
                  disabled={useAutoContext}
                  value={String(isHome)}
                  onChange={(event) => setIsHome(Number(event.target.value) as 0 | 1)}
                >
                  <option value="1">Home</option>
                  <option value="0">Away</option>
                </select>
              </label>
            </div>

            <label>
              Rest days
              <input
                type="range"
                min="0"
                max="7"
                value={restDays}
                disabled={useAutoContext}
                onChange={(event) => setRestDays(Number(event.target.value))}
              />
              <span className="range-value">{restDays}</span>
            </label>

            <button className="primary-button" type="submit" disabled={loading || !selectedPlayer}>
              {loading ? "Generating..." : "Predict next game stats"}
            </button>
          </form>

          {error ? <div className="error-banner">{error}</div> : null}
        </section>

        <section className="panel output-panel">
          <div className="panel-header">
            <p className="eyebrow">Output</p>
            <h2>Prediction summary</h2>
          </div>
          {prediction ? (
            <>
              <div className="context-row">
                <div>
                  <span>Player</span>
                  <strong>{prediction.player}</strong>
                </div>
                <div>
                  <span>Opponent</span>
                  <strong>{prediction.opponent}</strong>
                </div>
                <div>
                  <span>Location</span>
                  <strong>{prediction.is_home ? "Home" : "Away"}</strong>
                </div>
                <div>
                  <span>Rest</span>
                  <strong>{prediction.rest_days} days</strong>
                </div>
                <div>
                  <span>Data source</span>
                  <strong>{prediction.data_source}</strong>
                </div>
                <div>
                  <span>Context source</span>
                  <strong>{prediction.context_source}</strong>
                </div>
              </div>

              <div className="prediction-grid">
                {targets.map((target) => {
                  const result = prediction[target as Target];
                  const edge = result.mean - lines[target as Target];
                  const direction = Math.abs(edge) < 2 ? "Hold" : edge > 0 ? "Over" : "Under";
                  return (
                    <article key={target} className="prediction-card">
                      <p className="card-label">{target}</p>
                      <h3>{result.mean.toFixed(2)}</h3>
                      <p className="band-copy">
                        Range {result.lower.toFixed(2)} to {result.upper.toFixed(2)}
                      </p>
                      <label>
                        Line
                        <input
                          type="number"
                          step="0.5"
                          value={lines[target as Target]}
                          onChange={(event) =>
                            setLines((current) => ({
                              ...current,
                              [target]: Number(event.target.value),
                            }))
                          }
                        />
                      </label>
                      <div className="edge-row">
                        <span>{direction}</span>
                        <strong>{edge >= 0 ? "+" : ""}{edge.toFixed(2)}</strong>
                      </div>
                    </article>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="empty-state">
              <p>Run a prediction to see mean and uncertainty bands for all three targets.</p>
            </div>
          )}
        </section>

        <section className="panel insights-panel">
          <div className="panel-header">
            <p className="eyebrow">Analytics</p>
            <h2>Player context and recent form</h2>
          </div>
          {insights ? (
            <>
              <div className="summary-grid">
                <div className="summary-card">
                  <span>Last 5</span>
                  <strong>{insights.summary.last5_pts.toFixed(1)} PTS</strong>
                  <p>{insights.summary.last5_reb.toFixed(1)} REB / {insights.summary.last5_ast.toFixed(1)} AST</p>
                </div>
                <div className="summary-card">
                  <span>Last 10</span>
                  <strong>{insights.summary.last10_pts.toFixed(1)} PTS</strong>
                  <p>{insights.summary.last10_reb.toFixed(1)} REB / {insights.summary.last10_ast.toFixed(1)} AST</p>
                </div>
                <div className="summary-card">
                  <span>Last game</span>
                  <strong>{insights.summary.last_game_pts.toFixed(0)} PTS</strong>
                  <p>{insights.summary.last_game_reb.toFixed(0)} REB / {insights.summary.last_game_ast.toFixed(0)} AST</p>
                </div>
                <div className="summary-card">
                  <span>Source</span>
                  <strong>{insights.data_source}</strong>
                  <p>{insights.context_source}</p>
                </div>
              </div>

              <div className="table-card analysis-card">
                <h3>Recent games</h3>
                <div className="scroll-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Matchup</th>
                        <th>W/L</th>
                        <th>MIN</th>
                        <th>PTS</th>
                        <th>REB</th>
                        <th>AST</th>
                        <th>FGA</th>
                        <th>FTA</th>
                        <th>TOV</th>
                      </tr>
                    </thead>
                    <tbody>
                      {insights.recent_games.map((row) => (
                        <tr key={`${row.GAME_DATE}-${row.MATCHUP}`}>
                          <td>{row.GAME_DATE}</td>
                          <td>{row.MATCHUP}</td>
                          <td>{row.WL}</td>
                          <td>{row.MIN}</td>
                          <td>{row.PTS}</td>
                          <td>{row.REB}</td>
                          <td>{row.AST}</td>
                          <td>{row.FGA}</td>
                          <td>{row.FTA}</td>
                          <td>{row.TOV}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="empty-state">
              <p>Run a prediction to load player context and recent games.</p>
            </div>
          )}
        </section>

        <section className="panel model-panel">
          <div className="panel-header">
            <p className="eyebrow">Artifacts</p>
            <h2>Model metadata</h2>
          </div>
          <div className="model-list">
            {Object.entries(models).map(([target, metadata]) => (
              <article key={target} className="model-row">
                <div>
                  <p className="card-label">{target}</p>
                  <strong>{metadata.generated_at ? new Date(metadata.generated_at).toLocaleString() : "Unavailable"}</strong>
                </div>
                <div>
                  <span>MAE</span>
                  <strong>{metadata.metrics?.holdout.mae?.toFixed(3) ?? "--"}</strong>
                </div>
                <div>
                  <span>RMSE</span>
                  <strong>{metadata.metrics?.holdout.rmse?.toFixed(3) ?? "--"}</strong>
                </div>
                <div>
                  <span>Coverage</span>
                  <strong>{metadata.metrics?.holdout.interval_coverage?.toFixed(3) ?? "--"}</strong>
                </div>
                <div>
                  <span>Features</span>
                  <strong>{metadata.feature_columns?.length ?? 0}</strong>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="panel board-panel">
          <div className="panel-header board-header">
            <div>
              <p className="eyebrow">Prop board</p>
              <h2>Current props and ranked bets</h2>
            </div>
            <button className="secondary-button" type="button" onClick={handleRefreshBoard} disabled={refreshingBoard}>
              {refreshingBoard ? "Refreshing..." : "Refresh board predictions"}
            </button>
          </div>

          <div className="board-grid">
            <div className="table-card">
              <h3>Current props</h3>
              <div className="scroll-table">
                <table>
                  <thead>
                    <tr>
                      <th>Player</th>
                      <th>Stat</th>
                      <th>Line</th>
                    </tr>
                  </thead>
                  <tbody>
                    {props.map((row) => (
                      <tr key={`${row.player}-${row.stat}-${row.line}`}>
                        <td>{row.player}</td>
                        <td>{row.stat}</td>
                        <td>{row.line}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="table-card">
              <h3>Ranked bets</h3>
              {rankedBets.length > 0 ? (
                <div className="scroll-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Player</th>
                        <th>Stat</th>
                        <th>Edge</th>
                        <th>Recommendation</th>
                        <th>Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rankedBets.map((row) => (
                        <tr key={`${row.player}-${row.stat}-${row.generated_at}`}>
                          <td>{row.player}</td>
                          <td>{row.stat}</td>
                          <td>{row.edge?.toFixed(2)}</td>
                          <td>{row.recommendation}</td>
                          <td>{row.confidence}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="table-empty">No ranked bets yet. Refresh the board after the backend has usable data.</p>
              )}
            </div>
          </div>

          <div className="table-card analysis-card">
            <h3>Prediction pipeline results</h3>
            <div className="scroll-table">
              <table>
                <thead>
                  <tr>
                    <th>Player</th>
                    <th>Stat</th>
                    <th>Prediction</th>
                    <th>Edge</th>
                    <th>Data</th>
                    <th>Context</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {analysisRows.map((row) => (
                    <tr key={`${row.player}-${row.stat}-${row.generated_at}`}>
                      <td>{row.player}</td>
                      <td>{row.stat}</td>
                      <td>{row.prediction?.toFixed(2) ?? "--"}</td>
                      <td>{row.edge?.toFixed(2) ?? "--"}</td>
                      <td>{row.data_source ?? "--"}</td>
                      <td>{row.context_source ?? "--"}</td>
                      <td className="error-cell">{row.error || "--"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
