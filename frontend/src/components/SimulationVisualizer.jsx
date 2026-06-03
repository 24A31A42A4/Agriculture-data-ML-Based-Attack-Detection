import React, { useState, useEffect } from 'react';
import { Shield, AlertTriangle, CheckCircle, Info, Database, Cpu, Lock, Activity } from 'lucide-react';

const SimulationVisualizer = ({ traceData, attackType, onComplete }) => {
  const [visibleSteps, setVisibleSteps] = useState(0);

  useEffect(() => {
    setVisibleSteps(0);
    if (!traceData || traceData.length === 0) return;

    let currentStep = 0;
    const interval = setInterval(() => {
      currentStep += 1;
      setVisibleSteps(currentStep);
      if (currentStep >= traceData.length) {
        clearInterval(interval);
        if (onComplete) onComplete();
      }
    }, 1500); // 1.5 seconds per step

    return () => clearInterval(interval);
  }, [traceData]);

  if (!traceData || traceData.length === 0) {
    return null;
  }

  const getIcon = (stepName, status) => {
    const name = stepName.toLowerCase();
    if (name.includes('encryption') || name.includes('hash')) return <Lock size={20} />;
    if (name.includes('ml') || name.includes('model') || name.includes('predict')) return <Cpu size={20} />;
    if (name.includes('blockchain') || name.includes('ledger')) return <Database size={20} />;
    if (name.includes('payload') || name.includes('generate')) return <Activity size={20} />;
    
    switch (status) {
      case 'success': return <CheckCircle size={20} />;
      case 'error': return <AlertTriangle size={20} />;
      case 'warning': return <AlertTriangle size={20} />;
      default: return <Info size={20} />;
    }
  };

  const getColorClass = (status) => {
    switch (status) {
      case 'success': return 'bg-green-100 text-green-700 border-green-200';
      case 'error': return 'bg-red-100 text-red-700 border-red-200';
      case 'warning': return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      default: return 'bg-blue-100 text-blue-700 border-blue-200';
    }
  };

  const getLineColor = (status) => {
    switch (status) {
      case 'success': return 'bg-green-500';
      case 'error': return 'bg-red-500';
      case 'warning': return 'bg-yellow-500';
      default: return 'bg-blue-500';
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg p-6 font-mono text-gray-300 shadow-xl border border-gray-700 animate-in fade-in duration-300">
      <div className="flex items-center space-x-3 mb-6 border-b border-gray-700 pb-4">
        <Shield className="text-green-400 animate-pulse" size={24} />
        <h3 className="text-xl font-bold text-white uppercase tracking-wider">
          Attack Trace: {attackType.replace('_', ' ')}
        </h3>
      </div>

      <div className="space-y-0">
        {traceData.map((step, index) => {
          const isVisible = index < visibleSteps;
          if (!isVisible) return null;

          return (
            <div key={index} className="flex relative animate-in fade-in slide-in-from-left-4 duration-500">
              {/* Vertical line connecting nodes */}
              {index !== traceData.length - 1 && index < visibleSteps - 1 && (
                <div className={`absolute left-5 top-10 bottom-0 w-0.5 -ml-px ${getLineColor(step.status)} opacity-50`}></div>
              )}

              <div className="flex-shrink-0 mr-4 z-10 relative">
                <div className={`w-10 h-10 rounded-full border-2 flex items-center justify-center ${getColorClass(step.status)} shadow-lg`}>
                  {getIcon(step.step_name, step.status)}
                </div>
              </div>

              <div className="pb-8 flex-grow">
                <div className="bg-gray-800 border border-gray-700 rounded-md p-4 shadow-md relative overflow-hidden">
                  <div className={`absolute left-0 top-0 bottom-0 w-1 ${getLineColor(step.status)}`}></div>
                  <h4 className="text-lg font-bold text-gray-100 mb-1">{step.step_name}</h4>
                  <p className="text-sm text-gray-400 mb-2">{step.description}</p>
                  
                  {step.metadata && Object.keys(step.metadata).length > 0 && (
                    <div className="mt-3 bg-black rounded p-3 text-xs overflow-x-auto border border-gray-700">
                      <pre className="text-green-400">
                        {JSON.stringify(step.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
      
      {visibleSteps < traceData.length && (
        <div className="flex items-center space-x-2 text-green-400 text-sm mt-4 ml-4">
          <div className="w-2 h-2 rounded-full bg-green-400 animate-ping"></div>
          <span>Processing pipeline...</span>
        </div>
      )}
      
      {visibleSteps >= traceData.length && (
        <div className="flex justify-end mt-4">
          <span className="px-3 py-1 bg-gray-800 border border-gray-600 rounded text-xs text-gray-400 font-bold uppercase">
            Simulation Complete
          </span>
        </div>
      )}
    </div>
  );
};

export default SimulationVisualizer;
