import { useState, useMemo } from 'react'
import { useLocalStorage } from '../../hooks/useLocalStorage'
import {
  Plus, X, Dumbbell, Trophy, TrendingUp, ChevronDown, ChevronUp,
  Calendar, Zap, BarChart3, Check, Trash2
} from 'lucide-react'
import {
  generateId, calculate1RM, getPersonalRecords, suggestNextSession,
  calculateWeeklyVolume, COMMON_EXERCISES
} from '../../utils/fitness'

function SetRow({ set, onChange, onDelete }) {
  return (
    <div className="flex items-center gap-2 group">
      <span className="text-xs text-slate-600 w-6 text-center font-mono">{set.num}</span>
      <input type="number" value={set.weight || ''} onChange={e => onChange({ ...set, weight: parseFloat(e.target.value) || 0 })}
        placeholder="lbs" className="input w-20 text-sm text-center py-1" />
      <span className="text-slate-600 text-xs">×</span>
      <input type="number" value={set.reps || ''} onChange={e => onChange({ ...set, reps: parseInt(e.target.value) || 0 })}
        placeholder="reps" className="input w-16 text-sm text-center py-1" />
      {set.weight > 0 && set.reps > 0 && (
        <span className="text-xs text-slate-600 font-mono w-20">
          ~{calculate1RM(set.weight, set.reps).toFixed(0)} 1RM
        </span>
      )}
      <button onClick={onDelete} className="btn-icon opacity-0 group-hover:opacity-100 text-red-500 ml-auto">
        <X size={13} />
      </button>
    </div>
  )
}

function ExerciseBlock({ exercise, onChange, onDelete, workouts }) {
  const [open, setOpen] = useState(true)
  const suggestion = useMemo(() => suggestNextSession(exercise.name, workouts), [exercise.name, workouts])

  const addSet = () => {
    const lastSet = exercise.sets[exercise.sets.length - 1]
    const newSet = {
      id: generateId(),
      num: exercise.sets.length + 1,
      weight: suggestion?.weight || (lastSet?.weight ?? 0),
      reps:   suggestion?.reps  || (lastSet?.reps ?? 8),
    }
    onChange({ ...exercise, sets: [...exercise.sets, newSet] })
  }

  const updateSet = (id, updated) => {
    onChange({ ...exercise, sets: exercise.sets.map(s => s.id === id ? updated : s) })
  }

  const deleteSet = (id) => {
    const newSets = exercise.sets.filter(s => s.id !== id).map((s, i) => ({ ...s, num: i + 1 }))
    onChange({ ...exercise, sets: newSets })
  }

  const totalVol = exercise.sets.reduce((s, x) => s + (x.weight || 0) * (x.reps || 0), 0)

  return (
    <div className="card border-[#1e1e3f]">
      <div className="flex items-center gap-3 mb-3">
        <button onClick={() => setOpen(o => !o)} className="flex-1 flex items-center gap-2 text-left">
          <Dumbbell size={14} className="text-violet-400" />
          <span className="text-sm font-semibold text-slate-200">{exercise.name}</span>
          {exercise.muscleGroup && (
            <span className="text-xs text-slate-600 bg-slate-800 px-1.5 py-0.5 rounded">{exercise.muscleGroup}</span>
          )}
          <span className="text-xs text-slate-600 ml-auto">{totalVol > 0 ? `${totalVol.toLocaleString()} lbs vol` : ''}</span>
          {open ? <ChevronUp size={13} className="text-slate-600" /> : <ChevronDown size={13} className="text-slate-600" />}
        </button>
        <button onClick={onDelete} className="btn-icon text-red-500"><Trash2 size={14} /></button>
      </div>

      {open && (
        <>
          {suggestion && (
            <div className="mb-3 p-2 bg-violet-900/20 border border-violet-900/30 rounded-lg text-xs text-violet-300">
              <Zap size={10} className="inline mr-1" />
              Suggested: {suggestion.sets}×{suggestion.reps} @ {suggestion.weight} lbs — {suggestion.note}
            </div>
          )}

          <div className="space-y-2 mb-3">
            <div className="flex items-center gap-2 text-xs text-slate-600 px-1">
              <span className="w-6 text-center">#</span>
              <span className="w-20 text-center">Weight</span>
              <span className="w-16 text-center">Reps</span>
              <span className="w-20">Est 1RM</span>
            </div>
            {exercise.sets.map(set => (
              <SetRow key={set.id} set={set} onChange={updated => updateSet(set.id, updated)} onDelete={() => deleteSet(set.id)} />
            ))}
          </div>
          <button onClick={addSet} className="btn-ghost text-xs px-2 py-1">
            <Plus size={12} /> Add Set
          </button>
        </>
      )}
    </div>
  )
}

function WorkoutLogger({ workouts, onSave, onClose }) {
  const [exercises, setExercises] = useState([])
  const [workoutName, setWorkoutName] = useState('')
  const [customExercise, setCustomExercise] = useState('')
  const [selectedExercise, setSelectedExercise] = useState(COMMON_EXERCISES[0].name)

  const addExercise = (name, muscleGroup) => {
    if (!name.trim()) return
    setExercises(prev => [...prev, {
      id: generateId(),
      name: name.trim(),
      muscleGroup: muscleGroup || '',
      sets: [{ id: generateId(), num: 1, weight: 0, reps: 8 }],
    }])
  }

  const save = () => {
    const validExercises = exercises.filter(e => e.sets.some(s => s.weight > 0 && s.reps > 0))
    if (!validExercises.length) return
    onSave({
      id: generateId(),
      date: new Date().toISOString().split('T')[0],
      name: workoutName || new Date().toLocaleDateString('en-US', { weekday: 'long' }) + ' Workout',
      exercises: validExercises,
    })
    onClose()
  }

  return (
    <div className="card border-violet-900/40 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-200">Log Workout</h3>
        <button onClick={onClose} className="btn-icon"><X size={16} /></button>
      </div>

      <div>
        <label className="label">Workout Name (optional)</label>
        <input value={workoutName} onChange={e => setWorkoutName(e.target.value)}
          placeholder="Push Day, Leg Day..." className="input text-sm" />
      </div>

      <div className="flex gap-2">
        <select value={selectedExercise} onChange={e => setSelectedExercise(e.target.value)} className="select flex-1 text-sm">
          <optgroup label="Common Exercises">
            {COMMON_EXERCISES.map(ex => <option key={ex.name} value={ex.name}>{ex.name}</option>)}
          </optgroup>
        </select>
        <button onClick={() => {
          const ex = COMMON_EXERCISES.find(e => e.name === selectedExercise)
          addExercise(selectedExercise, ex?.muscleGroup)
        }} className="btn-secondary text-sm flex-shrink-0">
          <Plus size={14} /> Add
        </button>
      </div>

      <div className="flex gap-2">
        <input value={customExercise} onChange={e => setCustomExercise(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && (addExercise(customExercise), setCustomExercise(''))}
          placeholder="Or type custom exercise..." className="input flex-1 text-sm" />
        <button onClick={() => { addExercise(customExercise); setCustomExercise('') }}
          className="btn-ghost flex-shrink-0 text-sm">
          <Plus size={14} />
        </button>
      </div>

      <div className="space-y-3">
        {exercises.map(ex => (
          <ExerciseBlock
            key={ex.id}
            exercise={ex}
            onChange={updated => setExercises(prev => prev.map(e => e.id === ex.id ? updated : e))}
            onDelete={() => setExercises(prev => prev.filter(e => e.id !== ex.id))}
            workouts={workouts}
          />
        ))}
      </div>

      {exercises.length > 0 && (
        <button onClick={save} className="btn-primary w-full">
          <Check size={16} /> Save Workout
        </button>
      )}
    </div>
  )
}

function PRTable({ prs }) {
  const entries = Object.entries(prs)
  if (!entries.length) return <p className="text-xs text-slate-600">No PRs yet. Log some workouts!</p>

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-slate-600 uppercase tracking-wider border-b border-[#1e1e3f]">
            <th className="text-left py-2 font-medium">Exercise</th>
            <th className="text-right py-2 font-medium">Weight</th>
            <th className="text-right py-2 font-medium">Reps</th>
            <th className="text-right py-2 font-medium">Est 1RM</th>
            <th className="text-right py-2 font-medium">Date</th>
          </tr>
        </thead>
        <tbody>
          {entries.sort((a, b) => b[1].estimated1RM - a[1].estimated1RM).map(([name, pr]) => (
            <tr key={name} className="border-b border-[#1e1e3f]/40 hover:bg-[#111125]">
              <td className="py-2 text-slate-300">{name}</td>
              <td className="py-2 text-right font-mono text-slate-200">{pr.weight}</td>
              <td className="py-2 text-right font-mono text-slate-400">{pr.reps}</td>
              <td className="py-2 text-right font-mono text-violet-400 font-semibold">{pr.estimated1RM.toFixed(0)}</td>
              <td className="py-2 text-right text-slate-600 text-xs">
                {new Date(pr.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function FitnessTab() {
  const [workouts, setWorkouts] = useLocalStorage('os_workouts', [])
  const [logging, setLogging] = useState(false)
  const [activeSection, setActiveSection] = useState('log')

  const prs = useMemo(() => getPersonalRecords(workouts), [workouts])
  const weeklyVol = useMemo(() => calculateWeeklyVolume(workouts), [workouts])

  const saveWorkout = (workout) => setWorkouts(prev => [workout, ...prev])
  const deleteWorkout = (id) => setWorkouts(prev => prev.filter(w => w.id !== id))

  const recentWorkouts = workouts.slice(0, 10)

  return (
    <div className="tab-content space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Progressive Overload</h1>
          <p className="text-sm text-slate-500 mt-0.5">Track, progress, and peak</p>
        </div>
        <button onClick={() => setLogging(s => !s)} className="btn-primary">
          <Plus size={16} /> Log Workout
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="stat-card">
          <div className="stat-label">Workouts This Week</div>
          <div className="stat-value text-violet-400">{weeklyVol.workoutCount}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Weekly Volume</div>
          <div className="stat-value text-blue-400">{(weeklyVol.totalVolume / 1000).toFixed(1)}k <span className="text-sm">lbs</span></div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Exercises Tracked</div>
          <div className="stat-value text-slate-300">{Object.keys(prs).length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Workouts</div>
          <div className="stat-value text-slate-300">{workouts.length}</div>
        </div>
      </div>

      {logging && (
        <WorkoutLogger workouts={workouts} onSave={saveWorkout} onClose={() => setLogging(false)} />
      )}

      {/* Section tabs */}
      <div className="flex gap-1 border-b border-[#1e1e3f]">
        {[
          { id: 'log', label: 'History', icon: Calendar },
          { id: 'prs', label: 'Personal Records', icon: Trophy },
          { id: 'volume', label: 'Volume', icon: BarChart3 },
        ].map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setActiveSection(id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px
              ${activeSection === id ? 'border-violet-600 text-violet-400' : 'border-transparent text-slate-600 hover:text-slate-400'}`}>
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {activeSection === 'log' && (
        <div className="space-y-3">
          {recentWorkouts.length === 0 && (
            <div className="card text-center py-12">
              <Dumbbell size={32} className="mx-auto text-slate-700 mb-3" />
              <p className="text-slate-500 text-sm">No workouts yet. Log your first session!</p>
            </div>
          )}
          {recentWorkouts.map(workout => {
            const totalVol = workout.exercises.reduce((s, ex) =>
              s + ex.sets.reduce((ss, set) => ss + (set.weight || 0) * (set.reps || 0), 0), 0)
            const totalSets = workout.exercises.reduce((s, ex) => s + ex.sets.length, 0)
            return (
              <div key={workout.id} className="card card-hover group">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-slate-200">{workout.name}</span>
                    </div>
                    <div className="flex items-center gap-3 mt-1 flex-wrap">
                      <span className="text-xs text-slate-600">
                        <Calendar size={10} className="inline mr-1" />
                        {new Date(workout.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                      </span>
                      <span className="text-xs text-slate-600">{workout.exercises.length} exercises</span>
                      <span className="text-xs text-slate-600">{totalSets} sets</span>
                      {totalVol > 0 && <span className="text-xs text-violet-400 font-mono">{totalVol.toLocaleString()} lbs</span>}
                    </div>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {workout.exercises.map(ex => (
                        <span key={ex.id} className="text-xs bg-[#1e1e3f] text-slate-500 px-1.5 py-0.5 rounded">{ex.name}</span>
                      ))}
                    </div>
                  </div>
                  <button onClick={() => deleteWorkout(workout.id)} className="btn-icon opacity-0 group-hover:opacity-100 text-red-500 flex-shrink-0">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            )
          })}
          {workouts.length > 10 && (
            <p className="text-xs text-slate-600 text-center">Showing 10 most recent workouts</p>
          )}
        </div>
      )}

      {activeSection === 'prs' && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Trophy size={16} className="text-amber-400" />
            <h2 className="section-title">Personal Records</h2>
          </div>
          <PRTable prs={prs} />
        </div>
      )}

      {activeSection === 'volume' && (
        <div className="space-y-4">
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 size={16} className="text-blue-400" />
              <h2 className="section-title">Weekly Volume by Exercise</h2>
            </div>
            {Object.keys(weeklyVol.exerciseVolume).length === 0 ? (
              <p className="text-xs text-slate-600">No workouts this week.</p>
            ) : (
              <div className="space-y-2">
                {Object.entries(weeklyVol.exerciseVolume)
                  .sort((a, b) => b[1] - a[1])
                  .map(([name, vol]) => {
                    const pct = weeklyVol.totalVolume > 0 ? (vol / weeklyVol.totalVolume) * 100 : 0
                    return (
                      <div key={name}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-slate-400">{name}</span>
                          <span className="text-slate-500 font-mono">{vol.toLocaleString()} lbs</span>
                        </div>
                        <div className="h-1.5 bg-[#1e1e3f] rounded-full overflow-hidden">
                          <div className="h-full bg-violet-600 rounded-full transition-all" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    )
                  })}
              </div>
            )}
          </div>

          {Object.keys(weeklyVol.muscleGroupVolume).length > 0 && (
            <div className="card">
              <h2 className="section-title mb-4">By Muscle Group</h2>
              <div className="space-y-2">
                {Object.entries(weeklyVol.muscleGroupVolume)
                  .sort((a, b) => b[1] - a[1])
                  .map(([group, vol]) => {
                    const pct = weeklyVol.totalVolume > 0 ? (vol / weeklyVol.totalVolume) * 100 : 0
                    return (
                      <div key={group}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-slate-400">{group}</span>
                          <span className="text-slate-500 font-mono">{pct.toFixed(0)}%</span>
                        </div>
                        <div className="h-1.5 bg-[#1e1e3f] rounded-full overflow-hidden">
                          <div className="h-full bg-blue-600 rounded-full transition-all" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    )
                  })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
