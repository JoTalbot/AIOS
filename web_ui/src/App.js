import React, { useEffect, useState } from 'react';

function App() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch('/api/v1/stats')
      .then(res => res.json())
      .then(setStats);
  }, []);

  return (
    <div style={{ padding: 40, fontFamily: 'system-ui' }}>
      <h1>AIOS Dashboard v4.2</h1>
      {stats ? (
        <pre>{JSON.stringify(stats, null, 2)}</pre>
      ) : (
        <p>Loading...</p>
      )}
    </div>
  );
}

export default App;