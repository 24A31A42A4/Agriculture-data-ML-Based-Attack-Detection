import { useState, useEffect } from 'react';
import { ShieldAlert, Activity, Cpu, AlertCircle, CheckCircle2, Server, FileText, Database, Key, BarChart3, TrendingUp, RefreshCw } from 'lucide-react';
import { getHealthSummary, getActiveModels, triggerTamperingSimulation, triggerMLAnomalySimulation, compareMLPredictions, checkFeatureDrift, login, register, getDevices, getAuditLogs, getBlockchainBlocks, resetDeviceTrust } from '../services/api';
import SimulationVisualizer from './SimulationVisualizer';

export default function Dashboard() {
  const [healthData, setHealthData] = useState(null);
  const [models, setModels] = useState([]);
  const [devices, setDevices] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [blocks, setBlocks] = useState([]);
  
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));
  const [loginForm, setLoginForm] = useState({ username: 'admin@example.com', password: 'admin_password' });
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [registerForm, setRegisterForm] = useState({ full_name: 'New User', email: 'user@example.com', password: 'password123' });
  const [simResult, setSimResult] = useState(null);
  const [simType, setSimType] = useState('');
  const [loadingSim, setLoadingSim] = useState(false);
  const [loadingMLSim, setLoadingMLSim] = useState(false);
  const [driftData, setDriftData] = useState(null);
  const [compareData, setCompareData] = useState(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (isAuthenticated) {
      loadData();
    }
  }, [isAuthenticated, activeTab]);

  const loadData = async () => {
    try {
      if (activeTab === 'overview') {
        const [healthRes, modelsRes] = await Promise.all([
          getHealthSummary(),
          getActiveModels()
        ]);
        setHealthData(healthRes.data);
        setModels(modelsRes.data);
      } else if (activeTab === 'devices') {
        const res = await getDevices();
        setDevices(res.data);
      } else if (activeTab === 'audit') {
        const res = await getAuditLogs();
        setAuditLogs(res.data);
      } else if (activeTab === 'blockchain') {
        const res = await getBlockchainBlocks();
        setBlocks(res.data);
      } else if (activeTab === 'ml_analytics') {
        setLoadingAnalytics(true);
        try {
          const dummyFeatures = {
                "WaterLevel": 12.0, "Temperature": 38.0, "Humidity": 85.0, "Ph": 2.1, 
                "Rainfall": 0.0, "FertilizerApp": 1.0, "PesticideApp": 0.0, 
                "SoilMoisture": 98.0, "LightIntensity": 1000.0, "WindSpeed": 12.0, 
                "CO2Levels": 600.0, "PlantHeight": 40.0, "LeafAreaIndex": 2.5, "Yield": 0.0,
                "NDVI": 0.3, "SoilEC": 1.5, "SoilOrganicMatter": 3.0, "NitrogenLevel": 15.0,
                "PhosphorusLevel": 10.0, "PotassiumLevel": 20.0, "BatteryLevel": 90.0
          };
          const [driftRes, compareRes] = await Promise.all([
            checkFeatureDrift(),
            compareMLPredictions(dummyFeatures)
          ]);
          setDriftData(driftRes.data);
          setCompareData(compareRes.data);
        } catch(e) {
          console.error(e);
        } finally {
          setLoadingAnalytics(false);
        }
      }
    } catch (error) {
      console.error("Failed to fetch dashboard data", error);
      if (error.response?.status === 401) {
        setIsAuthenticated(false);
        localStorage.removeItem('token');
      }
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await login(loginForm.username, loginForm.password);
      localStorage.setItem('token', res.data.access_token);
      setIsAuthenticated(true);
    } catch (error) {
      alert("Login failed. Make sure backend is running and seeded.");
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      await register(registerForm);
      alert("Registration successful! You can now log in.");
      setIsRegisterMode(false);
    } catch (error) {
      alert("Registration failed. Make sure the backend is running or try a different email.");
    }
  };

  
  const handleResetTrust = async (deviceId) => {
    try {
      await resetDeviceTrust(deviceId);
      loadData();
    } catch (e) {
      console.error('Failed to reset trust', e);
    }
  };

  const runSimulation = async () => {
    setSimType('data_tampering');
    setLoadingSim(true);
    setSimResult(null);
    try {
      const dummyId = "00000000-0000-0000-0000-000000000000";
      const res = await triggerTamperingSimulation(dummyId);
      setSimResult(res.data);
      // Reload data to reflect changes
      loadData();
    } catch (error) {
      console.error("Sim error", error);
    } finally {
      setLoadingSim(false);
    }
  };

  const runMLSimulation = async () => {
    setSimType('ml_anomaly');
    setLoadingMLSim(true);
    setSimResult(null);
    try {
      const dummyId = "00000000-0000-0000-0000-000000000000";
      const res = await triggerMLAnomalySimulation(dummyId);
      setSimResult(res.data);
      loadData();
    } catch (error) {
      console.error("ML Sim error", error);
    } finally {
      setLoadingMLSim(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="max-w-md mx-auto mt-20 bg-white p-8 border border-gray-200 rounded-lg shadow-sm">
        <h2 className="text-2xl font-semibold mb-6 text-gray-900 text-center">
          {isRegisterMode ? "Register Account" : "Login Required"}
        </h2>
        {isRegisterMode ? (
          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Full Name</label>
              <input 
                type="text" 
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                value={registerForm.full_name} 
                onChange={e => setRegisterForm({...registerForm, full_name: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Email</label>
              <input 
                type="email" 
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                value={registerForm.email} 
                onChange={e => setRegisterForm({...registerForm, email: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Password</label>
              <input 
                type="password" 
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                value={registerForm.password} 
                onChange={e => setRegisterForm({...registerForm, password: e.target.value})}
              />
            </div>
            <button type="submit" className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none">
              Register
            </button>
            <div className="text-center mt-4">
              <button type="button" onClick={() => setIsRegisterMode(false)} className="text-sm text-blue-600 hover:text-blue-500">
                Already have an account? Log in
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Email</label>
              <input 
                type="text" 
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                value={loginForm.username} 
                onChange={e => setLoginForm({...loginForm, username: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Password</label>
              <input 
                type="password" 
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                value={loginForm.password} 
                onChange={e => setLoginForm({...loginForm, password: e.target.value})}
              />
            </div>
            <button type="submit" className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none">
              Sign In
            </button>
            <div className="text-center mt-4">
              <button type="button" onClick={() => setIsRegisterMode(true)} className="text-sm text-blue-600 hover:text-blue-500">
                Don't have an account? Register
              </button>
            </div>
          </form>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="border-b border-gray-200 bg-white px-4 pt-3 rounded-t-lg shadow-sm">
        <nav className="-mb-px flex space-x-8" aria-label="Tabs">
          {[
            { id: 'overview', name: 'Overview', icon: Activity },
            { id: 'devices', name: 'Device Fleet', icon: Server },
            { id: 'audit', name: 'Audit Trail', icon: FileText },
            { id: 'blockchain', name: 'Blockchain Explorer', icon: Database },
            { id: 'ml_analytics', name: 'ML Analytics & XAI', icon: BarChart3 },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                group inline-flex items-center py-3 px-2 border-b-2 font-medium text-sm transition-colors duration-200
                ${activeTab === tab.id 
                  ? 'border-blue-500 text-blue-600' 
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}
              `}
            >
              <tab.icon className={`mr-2 h-5 w-5 ${activeTab === tab.id ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'}`} />
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'overview' && (
          <div className="space-y-8 animate-in fade-in duration-300">
            {/* Top row metrics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm flex items-center space-x-4 hover:shadow-md transition-shadow">
                <div className="p-3 bg-blue-50 text-blue-600 rounded-full">
                  <Activity size={24} />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">System Health Score</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {healthData ? (healthData.average_health_score).toFixed(1) : '-'} / 100
                  </p>
                </div>
              </div>
              
              <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm flex items-center space-x-4 hover:shadow-md transition-shadow">
                <div className="p-3 bg-green-50 text-green-600 rounded-full">
                  <CheckCircle2 size={24} />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Healthy Devices</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {healthData ? healthData.healthy_devices_count : '-'}
                  </p>
                </div>
              </div>

              <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm flex items-center space-x-4 hover:shadow-md transition-shadow">
                <div className="p-3 bg-red-50 text-red-600 rounded-full">
                  <AlertCircle size={24} />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Degraded Devices</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {healthData ? healthData.degraded_devices_count : '-'}
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* ML Models */}
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200 flex items-center space-x-2 bg-gray-50">
                  <Cpu size={20} className="text-gray-500" />
                  <h3 className="text-lg font-medium text-gray-900">Active ML Models</h3>
                </div>
                <div className="p-6">
                  <div className="space-y-4">
                    {models.length > 0 ? models.map(model => (
                      <div key={model.id} className="flex justify-between items-center p-4 bg-white rounded-md border border-gray-200 hover:border-blue-300 transition-colors">
                        <div>
                          <p className="font-medium text-gray-900">{model.model_display_name}</p>
                          <p className="text-xs text-gray-500 mt-1">Type: {model.model_type}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-medium text-gray-900 bg-green-50 text-green-700 px-2 py-1 rounded inline-block">{(model.accuracy * 100).toFixed(2)}% Acc</p>
                          <p className="text-xs text-gray-500 mt-1">{model.avg_inference_time_ms.toFixed(1)}ms latency</p>
                        </div>
                      </div>
                    )) : (
                      <p className="text-gray-500 text-sm">No models registered or backend offline.</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Attack Simulation */}
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200 flex items-center space-x-2 bg-gray-50">
                  <ShieldAlert size={20} className="text-gray-500" />
                  <h3 className="text-lg font-medium text-gray-900">Attack Simulation</h3>
                </div>
                <div className="p-6 space-y-5">
                  <p className="text-sm text-gray-600 leading-relaxed">
                    Trigger a simulated data tampering attack against the security gateway. The system will detect hash mismatches, trigger an ML check, and autonomously drop the device trust score.
                  </p>
                  <button 
                    onClick={runSimulation}
                    disabled={loadingSim || loadingMLSim}
                    className="w-full py-3 bg-red-50 border border-red-200 rounded-md shadow-sm text-sm font-semibold text-red-700 hover:bg-red-100 focus:outline-none transition-colors flex justify-center items-center"
                  >
                    {loadingSim ? 'Running Simulation...' : 'Simulate Data Tampering'}
                  </button>
                  <button 
                    onClick={runMLSimulation}
                    disabled={loadingSim || loadingMLSim}
                    className="w-full py-3 bg-orange-50 border border-orange-200 rounded-md shadow-sm text-sm font-semibold text-orange-700 hover:bg-orange-100 focus:outline-none transition-colors flex justify-center items-center mt-3"
                  >
                    {loadingMLSim ? 'Running Simulation...' : 'Simulate ML Behavioral Anomaly'}
                  </button>
                  
                  {simResult && (
                    <div className="mt-6">
                      <SimulationVisualizer 
                        traceData={simResult.attack_trace} 
                        attackType={simResult.attack_type || simType} 
                        onComplete={() => console.log('Simulation UI completed')}
                      />
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'devices' && (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden animate-in fade-in duration-300">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
              <h3 className="text-lg font-medium text-gray-900">Registered Devices</h3>
              <p className="text-sm text-gray-500 mt-1">Live monitoring of device trust scores, roles, and lifecycle status.</p>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-white">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Device ID</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Name & Type</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Trust Score</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-100">
                  {devices.map((device) => (
                    <tr key={device.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-600">{device.device_id}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{device.device_name}</div>
                        <div className="text-xs text-gray-500">{device.device_type}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className={`h-2.5 w-2.5 rounded-full mr-2 shadow-sm ${device.trust_score >= 90 ? 'bg-green-500' : device.trust_score >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}></div>
                          <span className="text-sm font-semibold text-gray-900">{device.trust_score.toFixed(1)}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap flex items-center justify-between">
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
                      </td>
                    </tr>
                  ))}
                  {devices.length === 0 && (
                    <tr>
                      <td colSpan="4" className="px-6 py-8 text-center text-sm text-gray-500">No devices found.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'audit' && (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden animate-in fade-in duration-300">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
              <h3 className="text-lg font-medium text-gray-900">Immutable Audit Trail</h3>
              <p className="text-sm text-gray-500 mt-1">Log of critical security events. High severity events are cryptographically anchored to the blockchain.</p>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-white">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Timestamp</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Event & Severity</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Details</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Block Anchor</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-100">
                  {auditLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-500">{new Date(log.created_at).toLocaleString()}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-semibold text-gray-900 capitalize">{log.event_type.replace('_', ' ')}</div>
                        <div className={`text-xs mt-1 ${log.severity === 'high' || log.severity === 'critical' ? 'text-red-600 font-bold' : 'text-gray-500'}`}>{log.severity.toUpperCase()}</div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 break-words max-w-md">
                        {typeof log.event_details === 'object' ? (log.event_details.reason || JSON.stringify(log.event_details)) : log.event_details}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {log.blockchain_block_index !== null ? (
                          <span className="px-2 py-1 bg-green-50 text-green-700 rounded text-xs border border-green-200 font-mono shadow-sm">
                            Block #{log.blockchain_block_index}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400 italic">Unanchored</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {auditLogs.length === 0 && (
                    <tr>
                      <td colSpan="4" className="px-6 py-8 text-center text-sm text-gray-500">No audit logs found.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'blockchain' && (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden animate-in fade-in duration-300">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-medium text-gray-900">Blockchain Ledger</h3>
                <p className="text-sm text-gray-500 mt-1">Decentralized, immutable cryptographic history of the IoT system.</p>
              </div>
              <div className="px-3 py-1 bg-blue-50 border border-blue-200 rounded-md shadow-sm">
                <span className="text-xs font-semibold text-blue-700">Chain Height: {blocks.length}</span>
              </div>
            </div>
            <div className="p-6 space-y-6 bg-gray-50">
              {blocks.length === 0 ? (
                <p className="text-gray-500 text-sm text-center py-8">No blocks in the ledger.</p>
              ) : (
                [...blocks].reverse().map((block) => (
                  <div key={block.index} className="border border-gray-200 rounded-lg p-5 bg-white shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
                    {/* Decorative edge line */}
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500"></div>
                    
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex items-center space-x-3">
                        <div className="bg-blue-100 text-blue-700 rounded p-1.5 shadow-sm">
                          <Database size={18} />
                        </div>
                        <h4 className="text-lg font-bold text-gray-900">Block #{block.index}</h4>
                      </div>
                      <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded">{new Date(block.timestamp).toLocaleString()}</span>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-3">
                        <div>
                          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Block Hash</p>
                          <p className="text-xs font-mono text-gray-800 bg-gray-50 p-2 rounded border border-gray-100 truncate shadow-inner">{block.current_hash}</p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Previous Hash</p>
                          <p className="text-xs font-mono text-gray-500 bg-gray-50 p-2 rounded border border-gray-100 truncate">{block.previous_hash}</p>
                        </div>
                      </div>
                      <div className="space-y-3">
                        <div>
                          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Data Hash</p>
                          <p className="text-xs font-mono text-gray-600 bg-gray-50 p-2 rounded border border-gray-100 truncate">{block.data_hash}</p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Event Type</p>
                          <div className="flex space-x-2">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              {block.event_type.replace('_', ' ')}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
        {activeTab === 'ml_analytics' && (
          <div className="space-y-6 animate-in fade-in duration-300">
            {/* Feature Drift Panel */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex items-center space-x-2">
                <TrendingUp size={20} className="text-gray-500" />
                <h3 className="text-lg font-medium text-gray-900">Feature Drift Monitoring</h3>
              </div>
              <div className="p-6">
                {loadingAnalytics ? (
                  <p className="text-gray-500 text-sm">Loading drift analysis...</p>
                ) : driftData ? (
                  <div>
                    <div className="flex items-center space-x-2 mb-4">
                      <div className={`px-3 py-1 rounded-full text-xs font-bold ${driftData.overall_drift_detected ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
                        {driftData.overall_drift_detected ? 'DRIFT DETECTED' : 'NO SIGNIFICANT DRIFT'}
                      </div>
                      <span className="text-sm text-gray-500">Checking current sensor distribution against training baseline.</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {Object.entries(driftData?.features || {}).map(([feature, metrics]) => (
                        <div key={feature} className={`p-4 border rounded-lg ${metrics.drift_detected ? 'border-red-200 bg-red-50' : 'border-gray-200 bg-white'}`}>
                          <h4 className="font-semibold text-gray-900">{feature}</h4>
                          <p className="text-sm text-gray-600 mt-1">Wasserstein Dist: {metrics.wasserstein_distance.toFixed(3)}</p>
                          <p className={`text-xs font-bold mt-2 ${metrics.drift_detected ? 'text-red-600' : 'text-green-600'}`}>
                            {metrics.drift_detected ? 'Alert: Distribution Shift' : 'Stable'}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="text-gray-500 text-sm">Failed to load drift data.</p>
                )}
              </div>
            </div>

            {/* Model Comparison & XAI Panel */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex items-center space-x-2">
                <BarChart3 size={20} className="text-gray-500" />
                <h3 className="text-lg font-medium text-gray-900">Explainable AI & Model Comparison</h3>
              </div>
              <div className="p-6">
                {loadingAnalytics ? (
                  <p className="text-gray-500 text-sm">Running inferences...</p>
                ) : compareData ? (
                  <div className="space-y-6">
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                      <h4 className="text-sm font-bold text-blue-900 uppercase tracking-wide">Primary IDS Engine: Stacking Classifier</h4>
                      <p className="text-sm text-blue-800 mt-1">The system uses the ensemble consensus (Stacking) to drive adaptive security responses.</p>
                      <div className="mt-3 flex items-center space-x-4">
                        <span className="px-3 py-1 bg-blue-600 text-white font-bold rounded shadow-sm text-sm">
                          Consensus: {compareData.consensus.majority_vote}
                        </span>
                        <span className="text-sm text-blue-700 font-medium">
                          Agreement: {(compareData.consensus.agreement_ratio * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      {compareData.predictions.map((pred, idx) => (
                        <div key={idx} className={`p-4 border rounded-lg shadow-sm ${pred.label === 'Anomaly' ? 'border-orange-200 bg-orange-50' : 'border-gray-200 bg-white'}`}>
                          <h4 className="font-bold text-gray-900 text-sm truncate" title={pred.model_name}>{pred.model_name}</h4>
                          <div className="mt-3 space-y-2">
                            <div className="flex justify-between items-center">
                              <span className="text-xs text-gray-500">Prediction:</span>
                              <span className={`text-xs font-bold px-2 py-0.5 rounded ${pred.label === 'Anomaly' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
                                {pred.label}
                              </span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="text-xs text-gray-500">Probability:</span>
                              <span className="text-xs font-mono font-medium">
                                {pred.probability ? (pred.probability * 100).toFixed(1) + '%' : 'N/A'}
                              </span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="text-xs text-gray-500">Latency:</span>
                              <span className="text-xs font-mono text-gray-600">{pred.inference_time_ms.toFixed(1)}ms</span>
                            </div>
                          </div>
                          
                          {/* Top Features (XAI) */}
                          {pred.top_features && (
                            <div className="mt-4 pt-3 border-t border-gray-200">
                              <span className="text-xs font-semibold text-gray-700">Top Drivers:</span>
                              <ul className="mt-1 space-y-1">
                                {pred.top_features.map((f, i) => (
                                  <li key={i} className="text-xs text-gray-600 flex justify-between">
                                    <span className="truncate pr-2">{f.feature}</span>
                                    <span className="font-mono text-gray-400">{(f.importance * 100).toFixed(0)}%</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="text-gray-500 text-sm">Failed to load comparison data.</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
