import re
import os

path = r"c:\Users\Alisha\Desktop\Agri_another\Agriculture-data-ML-Based-Attack-Detection\frontend\src\components\Dashboard.jsx"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Imports
content = content.replace(
    "import { getHealthSummary, getActiveModels, triggerTamperingSimulation, triggerMLAnomalySimulation, compareMLPredictions, checkFeatureDrift, login, register, getDevices, getAuditLogs, getBlockchainBlocks } from '../services/api';",
    "import { getHealthSummary, getActiveModels, triggerTamperingSimulation, triggerMLAnomalySimulation, compareMLPredictions, checkFeatureDrift, login, register, getDevices, getAuditLogs, getBlockchainBlocks, resetDeviceTrust } from '../services/api';\nimport SimulationVisualizer from './SimulationVisualizer';"
)
content = content.replace("import { ShieldAlert, Activity, Cpu, AlertCircle, CheckCircle2, Server, FileText, Database, Key, BarChart3, TrendingUp } from 'lucide-react';", "import { ShieldAlert, Activity, Cpu, AlertCircle, CheckCircle2, Server, FileText, Database, Key, BarChart3, TrendingUp, RefreshCw } from 'lucide-react';")

# 2. State for simType
content = content.replace(
    "const [simResult, setSimResult] = useState(null);",
    "const [simResult, setSimResult] = useState(null);\n  const [simType, setSimType] = useState('');"
)

# 3. Handle reset trust
reset_trust_fn = """
  const handleResetTrust = async (deviceId) => {
    try {
      await resetDeviceTrust(deviceId);
      loadData();
    } catch (e) {
      console.error('Failed to reset trust', e);
    }
  };
"""
content = content.replace("const runSimulation = async () => {", reset_trust_fn + "\n  const runSimulation = async () => {\n    setSimType('data_tampering');")
content = content.replace("const runMLSimulation = async () => {", "const runMLSimulation = async () => {\n    setSimType('ml_anomaly');")

# 4. Replace basic simulation UI with Visualizer
sim_ui_old = """                  {simResult && (
                    <div className="mt-4 p-4 rounded-md border border-red-200 bg-red-50 animate-in slide-in-from-top-2">
                      <div className="flex">
                        <div className="flex-shrink-0">
                          <ShieldAlert className="h-5 w-5 text-red-600" aria-hidden="true" />
                        </div>
                        <div className="ml-3">
                          <h3 className="text-sm font-bold text-red-800">
                            {simResult.was_detected ? 'Attack Detected & Blocked' : 'Attack Succeeded'}
                          </h3>
                          <div className="mt-2 text-sm text-red-700 space-y-1">
                            <p><strong>Layer:</strong> <span className="font-mono bg-red-100 px-1 rounded">{simResult.detection_layer}</span></p>
                            <p><strong>Penalty:</strong> <span className="font-bold">{simResult.trust_score_penalty}</span> Trust Points</p>
                            <p className="mt-2 text-xs opacity-90">{simResult.details}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}"""

sim_ui_new = """                  {simResult && (
                    <div className="mt-6">
                      <SimulationVisualizer 
                        traceData={simResult.attack_trace} 
                        attackType={simResult.attack_type || simType} 
                        onComplete={() => console.log('Simulation UI completed')}
                      />
                    </div>
                  )}"""
content = content.replace(sim_ui_old, sim_ui_new)

# 5. Add reset trust button to devices table
device_td_old = """                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2.5 py-1 inline-flex text-xs leading-5 font-semibold rounded-full border ${device.lifecycle_status === 'registered' ? 'bg-blue-50 border-blue-200 text-blue-700' : 'bg-gray-50 border-gray-200 text-gray-700'}`}>
                          {device.lifecycle_status}
                        </span>
                      </td>"""

device_td_new = """                      <td className="px-6 py-4 whitespace-nowrap flex items-center justify-between">
                        <span className={`px-2.5 py-1 inline-flex text-xs leading-5 font-semibold rounded-full border ${device.lifecycle_status === 'registered' ? 'bg-blue-50 border-blue-200 text-blue-700' : 'bg-gray-50 border-gray-200 text-gray-700'}`}>
                          {device.lifecycle_status}
                        </span>
                        <button 
                          onClick={() => handleResetTrust(device.device_id)}
                          title="Reset Trust Score to 100.0"
                          className="text-gray-400 hover:text-blue-600 transition-colors ml-4"
                        >
                          <RefreshCw size={16} />
                        </button>
                      </td>"""
content = content.replace(device_td_old, device_td_new)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
