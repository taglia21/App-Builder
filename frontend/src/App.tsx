import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Landing from './components/Landing';
import Dashboard from './components/Dashboard';

function App() {
  const [isLaunched, setIsLaunched] = useState(false);

  return (
    <div style={{ position: 'relative', width: '100vw', height: '100vh', overflow: 'hidden', background: 'black' }}>

      {/* Dashboard Layer (Behind) */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={isLaunched ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.95 }}
        transition={{ duration: 1.5, delay: 0.5 }}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          zIndex: 1
        }}
      >
        <Dashboard />
      </motion.div>

      {/* Landing Layer (Front) */}
      <motion.div
        initial={{ y: 0 }}
        animate={isLaunched ? { y: '-100vh' } : { y: 0 }}
        transition={{ duration: 1.5, ease: [0.6, 0.05, -0.01, 0.9] }} // Custom ease for cinematic feel
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          zIndex: 10,
          background: 'transparent' // Background is handled by body gradient
        }}
      >
        <Landing onLaunch={() => setIsLaunched(true)} />
      </motion.div>

    </div>
  );
}

export default App;
