// Loads every font of the registry (fonts/fonts.json) from the library's own files: no network at render
// time (design §11). FontGate holds the first frame until they are loaded, so text measured for fitting
// uses the real fonts.
import React, {useEffect, useState} from 'react';
import {continueRender, delayRender, staticFile} from 'remotion';
import {loadFont} from '@remotion/fonts';
import registry from '../fonts/fonts.json' with {type: 'json'};

type FontEntry = {file: string; weight: string};
const entries = Object.entries(registry.fonts as Record<string, FontEntry>);

const fontsReady = Promise.all(
  entries.map(([family, f]) => loadFont({family, url: staticFile(f.file), weight: f.weight})),
);

export const FontGate: React.FC<{children: React.ReactNode}> = ({children}) => {
  const [handle] = useState(() => delayRender('loading the library fonts'));
  const [ready, setReady] = useState(false);
  useEffect(() => {
    fontsReady.then(() => {
      setReady(true);
      continueRender(handle);
    });
  }, [handle]);
  return ready ? <>{children}</> : null;
};
