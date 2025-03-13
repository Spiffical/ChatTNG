import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { MantineProvider, createTheme } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Analytics } from "@vercel/analytics/react";
import { ChatInterface } from './components/ChatInterface';
import { SharedConversation } from './components/SharedConversation';
import { useEffect } from 'react';

const queryClient = new QueryClient();

const theme = createTheme({
  colors: {
    // Deep space blues for Star Trek theme
    brand: [
      '#001f3f', // darkest navy
      '#00264d',
      '#003366',
      '#004080',
      '#004d99',
      '#0059b3',
      '#0066cc',
      '#0073e6',
      '#0080ff',
      '#008cff',
    ],
  },
  primaryColor: 'brand',
  // Modern, clean font stack
  fontFamily: 'Inter, system-ui, Avenir, Helvetica, Arial, sans-serif',
});

export const App = () => {
  useEffect(() => {
    console.log('App mounted, logging test:', {
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      isIOS: /iPad|iPhone|iPod/.test(navigator.userAgent) || 
        (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
    });
    // Pre-create a pool of stars to reuse
    const starPool = Array.from({ length: 50 }, () => {
      const star = document.createElement('div');
      star.className = 'star';
      return star;
    });
    let activeStars = new Set<HTMLDivElement>();

    const reuseOrCreateStar = () => {
      // Try to get an inactive star from the pool
      const star = starPool.find(s => !activeStars.has(s));
      if (star) {
        activeStars.add(star);
        return star;
      }
      return null; // Pool is full
    };

    const createStar = () => {
      const star = reuseOrCreateStar();
      if (!star) return; // Skip if pool is full
      
      // Calculate a random starting position near the center
      const centerX = window.innerWidth / 2;
      const centerY = window.innerHeight / 2;
      const spawnRadius = 150;
      const spawnAngle = Math.random() * Math.PI * 2;
      const spawnDistance = Math.random() * spawnRadius;
      const startX = Math.cos(spawnAngle) * spawnDistance;
      const startY = Math.sin(spawnAngle) * spawnDistance;
      
      // Set initial position
      star.style.left = `${centerX}px`;
      star.style.top = `${centerY}px`;
      star.style.setProperty('--start-x', `${startX}px`);
      star.style.setProperty('--start-y', `${startY}px`);
      
      // Determine which edge is closest based on spawn position
      const relativeX = startX / centerX;
      const relativeY = startY / centerY;
      
      // Calculate end point based on closest edge
      let endX, endY;
      
      if (Math.abs(relativeX) > Math.abs(relativeY)) {
        endX = relativeX > 0 ? window.innerWidth - centerX : -centerX;
        const ratio = Math.abs(endX / startX);
        endY = startY * ratio;
      } else {
        endY = relativeY > 0 ? window.innerHeight - centerY : -centerY;
        const ratio = Math.abs(endY / startY);
        endX = startX * ratio;
      }
      
      star.style.setProperty('--tx', `${endX}px`);
      star.style.setProperty('--ty', `${endY}px`);
      
      // Optimize distance calculation
      const distance = Math.hypot(endX, endY);
      const duration = distance * 2; // Simplified speed calculation
      
      star.style.animationDuration = `${duration}ms`;
      
      if (!star.isConnected) {
        document.body.appendChild(star);
      }
      
      // Schedule cleanup
      setTimeout(() => {
        if (star.isConnected) {
          document.body.removeChild(star);
        }
        activeStars.delete(star);
      }, duration);
    };
    
    // Use requestAnimationFrame for smoother performance
    let lastSpawn = 0;
    const spawnInterval = 100; // Time between spawn attempts
    
    const animate = (timestamp: number) => {
      if (timestamp - lastSpawn >= spawnInterval) {
        const starsToCreate = Math.floor(Math.random() * 2);
        for (let i = 0; i < starsToCreate; i++) {
          createStar();
        }
        lastSpawn = timestamp;
      }
      animationFrame = requestAnimationFrame(animate);
    };
    
    let animationFrame = requestAnimationFrame(animate);
    
    // Handle window resize
    const handleResize = () => {
      activeStars.forEach(star => {
        if (star.isConnected) {
          document.body.removeChild(star);
        }
      });
      activeStars.clear();
    };
    
    window.addEventListener('resize', handleResize);
    
    return () => {
      cancelAnimationFrame(animationFrame);
      window.removeEventListener('resize', handleResize);
      activeStars.forEach(star => {
        if (star.isConnected) {
          document.body.removeChild(star);
        }
      });
      activeStars.clear();
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={theme} defaultColorScheme="dark">
        <Notifications />
        <Router>
          <Routes>
            <Route path="/" element={<ChatInterface />} />
            <Route path="/share/:shareId" element={<SharedConversation />} />
          </Routes>
        </Router>
        <Analytics />
      </MantineProvider>
    </QueryClientProvider>
  );
};

export default App;
