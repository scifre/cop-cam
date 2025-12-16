/**
 * Simulation clock using master video time
 */
class SimulationClock {
  constructor(masterVideoRef, onTimeUpdate) {
    this.masterVideoRef = masterVideoRef
    this.onTimeUpdate = onTimeUpdate
    this.lastTime = 0
    this.isPlaying = false
    this.animationFrameId = null
  }

  start() {
    if (this.isPlaying) return
    
    this.isPlaying = true
    this.lastTime = this.getCurrentTime()
    this.tick()
  }

  stop() {
    this.isPlaying = false
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId)
      this.animationFrameId = null
    }
  }

  getCurrentTime() {
    if (!this.masterVideoRef?.current) return 0
    return this.masterVideoRef.current.currentTime || 0
  }

  tick = () => {
    if (!this.isPlaying) return

    const currentTime = this.getCurrentTime()
    
    if (currentTime !== this.lastTime) {
      this.onTimeUpdate(this.lastTime, currentTime)
      this.lastTime = currentTime
    }

    this.animationFrameId = requestAnimationFrame(this.tick)
  }

  reset() {
    this.lastTime = 0
  }
}

export { SimulationClock }

