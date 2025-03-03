
const { createApp, ref, onMounted, computed } = Vue;

createApp({
    delimiters: ['${', '}'],
    setup() {
        // State
        const currentView = ref('dashboard');
        const plugins = ref({});
        const experimentsData = ref({ tests: [] });
        const globalConfig = ref({});
        const loading = ref(false);
        const notification = ref({ show: false, message: '', type: 'info' });
        const runningExperiment = ref(null);
        const experimentResults = ref([]);

        // Load data on mount
        onMounted(async () => {
            await Promise.all([
                loadPlugins(),
                loadExperiments(),
                loadGlobalConfig()
            ]);
        });

        // Computed properties
        const experiments = computed(() => {
            return experimentsData.value.tests || [];
        });

        // Methods
        const loadPlugins = async () => {
            try {
                loading.value = true;
                const response = await axios.get('/api/plugins');
                plugins.value = response.data;
            } catch (error) {
                showNotification('Failed to load plugins: ' + error.message, 'danger');
            } finally {
                loading.value = false;
            }
        };

        const loadExperiments = async () => {
            try {
                loading.value = true;
                const response = await axios.get('/api/experiments');
                experimentsData.value = response.data;
            } catch (error) {
                showNotification('Failed to load experiments: ' + error.message, 'danger');
            } finally {
                loading.value = false;
            }
        };

        const loadGlobalConfig = async () => {
            try {
                // This would be an actual endpoint in a full implementation
                globalConfig.value = {
                    "logging": {
                        "level": "DEBUG",
                        "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
                    },
                    "paths": {
                        "output_dir": "outputs",
                        "log_dir": "outputs/logs",
                        "config_dir": "configs",
                        "plugin_dir": "plugins"
                    },
                    "docker": {
                        "build_docker_image": true
                    },
                    "features": {
                        "logger_observer": true,
                        "storage_handler": true,
                        "fast_fail": true
                    }
                };
            } catch (error) {
                showNotification('Failed to load global config: ' + error.message, 'danger');
            }
        };

        const runExperiment = async (testName) => {
            try {
                loading.value = true;
                runningExperiment.value = testName;
                showNotification(`Starting experiment: ${testName}`, 'info');
                
                const response = await axios.post('/api/run-experiment', { test_name: testName });
                
                if (response.data.status === 'success') {
                    showNotification(`Experiment ${testName} completed successfully`, 'success');
                    experimentResults.value.unshift({
                        name: testName,
                        date: new Date().toLocaleString(),
                        status: 'Completed',
                        result: response.data.result
                    });
                } else {
                    showNotification(`Experiment ${testName} failed: ${response.data.message}`, 'danger');
                }
            } catch (error) {
                showNotification(`Failed to run experiment: ${error.message}`, 'danger');
            } finally {
                loading.value = false;
                runningExperiment.value = null;
            }
        };

        const showNotification = (message, type = 'info') => {
            notification.value = {
                show: true,
                message,
                type
            };
            
            setTimeout(() => {
                notification.value.show = false;
            }, 5000);
        };

        return {
            currentView,
            plugins,
            experimentsData,
            experiments,
            globalConfig,
            loading,
            notification,
            runningExperiment,
            experimentResults,
            runExperiment,
            showNotification
        };
    }
}).mount('#app');
