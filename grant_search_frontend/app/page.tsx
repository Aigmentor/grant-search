'use client';

import { Button } from 'antd';
import { redirect } from 'next/navigation';
import { useState } from 'react';

export default function Home() {
  return redirect('/grants');
}
//   const [displayed, setDisplayed] = useState(false);
//   return (
//     <div className="container mx-auto px-4 py-8">
//       <h1 className="text-4xl font-bold mb-6">Welcome to Doge Afuera</h1>
      
//       <div className="mb-8">
//         <p className="text-lg mb-4">
//           Doge Afuera is a project to find and &quot;afuera&quot; terrible government grant spendings.
//           We&apos;ve indexed thousands of grants from the US government and are using AI to find the worst of the worst.          
//         </p>
//         <p className="text-lg mb-4">
//           Search for grants using natural language, find the worst offenders and....
//         </p>
//         <Button
//           type="primary"
//           danger
//           onClick={() => {setDisplayed(true)}}
//         >
//           AFUERA!
//         </Button>
//         &nbsp;
//         <Button
//           type="primary"
//           style={{
//             opacity: displayed ? 1 : 0,
//             transition: 'opacity 2.2s',
//           }}

//           onClick={() => {window.location.href = '/grants'}}
//         >
//           Let&apos;s Go!
//         </Button>
//       </div>

//       <div className="grid md:grid-cols-2 gap-8">
//         <div className="flex flex-col items-center">
//           <img 
//             src="/static/javier-chainsaw.gif"
//             alt="Javier Milie with a chainsaw"
//             className="rounded-lg shadow-lg mb-2 max-w-full h-auto"
//             style={{display: displayed ? 'block' : 'none'}}
//           />
//         </div>
//         <div className="flex flex-col items-center">
//           <img
//             src="/static/javier-milei-afuera.gif" 
//             alt="Javier Milie afuera"
//             className="rounded-lg shadow-lg mb-2 max-w-full h-auto"
//             style={{display: displayed ? 'block' : 'none'}}
//           />
//         </div>
//       </div>
//     </div>
//   );
// }