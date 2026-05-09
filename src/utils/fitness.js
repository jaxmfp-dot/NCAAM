export function generateId() {
  return `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
}

export function calculate1RM(weight, reps) {
  if (reps === 1) return weight
  return Math.round(weight * (1 + reps / 30) * 10) / 10
}

export function estimateWeight(oneRM, reps) {
  return Math.round((oneRM / (1 + reps / 30)) * 4) / 4
}

export function getPersonalRecords(workouts) {
  const prs = {}
  for (const workout of workouts) {
    for (const exercise of workout.exercises || []) {
      for (const set of exercise.sets || []) {
        if (!set.weight || !set.reps) continue
        const estimated1RM = calculate1RM(set.weight, set.reps)
        if (!prs[exercise.name] || estimated1RM > prs[exercise.name].estimated1RM) {
          prs[exercise.name] = {
            weight: set.weight,
            reps: set.reps,
            estimated1RM,
            date: workout.date,
          }
        }
      }
    }
  }
  return prs
}

export function suggestNextSession(exerciseName, workouts) {
  const recentWorkout = [...workouts]
    .reverse()
    .find(w => w.exercises?.some(e => e.name === exerciseName))

  if (!recentWorkout) return null

  const lastExercise = recentWorkout.exercises.find(e => e.name === exerciseName)
  if (!lastExercise?.sets?.length) return null

  const validSets = lastExercise.sets.filter(s => s.weight && s.reps)
  if (!validSets.length) return null

  const avgWeight = validSets.reduce((s, x) => s + x.weight, 0) / validSets.length
  const targetReps = validSets[0].reps

  const isUpperBody = /bench|press|curl|row|pull|push|fly|tricep|bicep|shoulder|lat|chest/i.test(exerciseName)
  const increment = isUpperBody ? 2.5 : 5

  const suggestion = {
    sets: validSets.length,
    reps: targetReps,
    weight: Math.round((avgWeight + increment) * 4) / 4,
    note: `+${increment} lbs progression from ${avgWeight} lbs`,
    lastDate: recentWorkout.date,
  }

  return suggestion
}

export function calculateWeeklyVolume(workouts) {
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - 7)
  cutoff.setHours(0, 0, 0, 0)

  const weeklyWorkouts = workouts.filter(w => new Date(w.date) >= cutoff)

  let totalVolume = 0
  const exerciseVolume = {}
  const muscleGroupVolume = {}

  for (const workout of weeklyWorkouts) {
    for (const exercise of workout.exercises || []) {
      const vol = (exercise.sets || []).reduce((s, x) => s + (x.weight || 0) * (x.reps || 0), 0)
      totalVolume += vol
      exerciseVolume[exercise.name] = (exerciseVolume[exercise.name] || 0) + vol
      const group = exercise.muscleGroup || 'Other'
      muscleGroupVolume[group] = (muscleGroupVolume[group] || 0) + vol
    }
  }

  return {
    totalVolume: Math.round(totalVolume),
    exerciseVolume,
    muscleGroupVolume,
    workoutCount: weeklyWorkouts.length,
    sessions: weeklyWorkouts,
  }
}

export const COMMON_EXERCISES = [
  { name: 'Bench Press', muscleGroup: 'Chest' },
  { name: 'Incline Bench Press', muscleGroup: 'Chest' },
  { name: 'Dumbbell Fly', muscleGroup: 'Chest' },
  { name: 'Push-Up', muscleGroup: 'Chest' },
  { name: 'Squat', muscleGroup: 'Legs' },
  { name: 'Romanian Deadlift', muscleGroup: 'Legs' },
  { name: 'Leg Press', muscleGroup: 'Legs' },
  { name: 'Leg Curl', muscleGroup: 'Legs' },
  { name: 'Calf Raise', muscleGroup: 'Legs' },
  { name: 'Deadlift', muscleGroup: 'Back' },
  { name: 'Pull-Up', muscleGroup: 'Back' },
  { name: 'Barbell Row', muscleGroup: 'Back' },
  { name: 'Cable Row', muscleGroup: 'Back' },
  { name: 'Lat Pulldown', muscleGroup: 'Back' },
  { name: 'Overhead Press', muscleGroup: 'Shoulders' },
  { name: 'Lateral Raise', muscleGroup: 'Shoulders' },
  { name: 'Face Pull', muscleGroup: 'Shoulders' },
  { name: 'Barbell Curl', muscleGroup: 'Arms' },
  { name: 'Tricep Pushdown', muscleGroup: 'Arms' },
  { name: 'Hammer Curl', muscleGroup: 'Arms' },
  { name: 'Plank', muscleGroup: 'Core' },
  { name: 'Cable Crunch', muscleGroup: 'Core' },
]
