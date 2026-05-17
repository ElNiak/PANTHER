/**
 * topology_nav.js - Navigation helper for topology node clicks.
 * 
 * When a node is clicked on the topology diagram, this script is injected
 * to navigate to the config builder page with the correct query parameters.
 * It also logs debug information to the browser console.
 */

window.pantherTopologyNav = {
    /**
     * Navigate to the config builder with node context.
     * 
     * @param {string} configPath - The path to the config file
     * @param {number} testIndex - The index of the test containing the service
     * @param {string} serviceId - The ID of the service node
     * @param {string} serviceName - The display name of the service
     */
    navigateToConfig: function(configPath, testIndex, serviceId, serviceName) {
        const params = new URLSearchParams({
            config_path: configPath || '',
            test_index: String(testIndex ?? ''),
            service_id: serviceId || '',
            service_name: serviceName || '',
            source: 'topology'
        });
        
        const targetUrl = '/config?' + params.toString();
        
        // Debug logging to verify values
        console.log('=== PANTHER Topology Navigation ===');
        console.log('Navigating to:', targetUrl);
        console.log('configPath:', configPath);
        console.log('testIndex:', testIndex);
        console.log('serviceId:', serviceId);
        console.log('serviceName:', serviceName);
        console.log('timestamp:', new Date().toISOString());
        console.log('===================================');
        
        // Navigate to the config builder page
        // Using direct location change for cross-page navigation
        window.location.href = targetUrl;
    },
    
    /**
     * Log node data for debugging without navigation.
     * Used during development to verify click data.
     */
    logNodeData: function(nodeData) {
        console.log('=== PANTHER Topology Node Click Debug ===');
        console.log('Node data received:', JSON.stringify(nodeData, null, 2));
        console.log('========================================');
    }
};