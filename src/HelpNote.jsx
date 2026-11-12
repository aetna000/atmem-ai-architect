import React from 'react';
export function HelpNote({label,children}){return <details className="help-note"><summary aria-label={label||'More information'} title={label||'More information'}>?</summary><div>{children}</div></details>;}
