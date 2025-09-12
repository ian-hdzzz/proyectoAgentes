using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;

[System.Serializable]
public class FireData
{
    public int row;
    public int col;
}

[System.Serializable]
public class FireResponse
{
    public FireData[] fires;
}

[System.Serializable]
public class AgentData
{
    public int id;
    public int x;
    public int y;
    public string role; 
    public bool knocked_out;
    public bool isCarryingVictim;  // Indica si el agente está cargando una víctima
    public POIData targetPOI;      // El POI objetivo del agente
}

[System.Serializable]
public class AgentResponse
{
    public AgentData[] agents;
}

[System.Serializable]
public class StepResponse
{
    public string message;
    public int step;
    public FireData[] fires;
    public AgentData[] agents;
}

[System.Serializable]
public class POIData
{
    public int x;
    public int y;
    public string type; 
    public bool revealed;
}

[System.Serializable]
public class POIResponse
{
    public POIData[] pois;
}

[System.Serializable]
public class SmokeData
{
    public int row;
    public int col;
}

[System.Serializable]
public class SmokeResponse
{
    public SmokeData[] smoke;
}

[System.Serializable]
public class RevealPOIResponse
{
    public bool success;
    public string poiType;     
    public bool wasRevealed;
    public string message;
}

[System.Serializable]
public class GameStateData
{
    public string phase;         
    public int currentAgent;     // índice del agente actual
    public int damageCount;      // contador de daño estructural
    public int roundCount;       // contador de rondas
    public bool gameOver;        // si el juego ha terminado
    public bool gameWon;        // si el juego se ganó
    public string endReason;     // razón del fin del juego
}

[System.Serializable]
public class GameStateResponse
{
    public GameStateData gameState;
}

public class FireManager : MonoBehaviour
{
    [Header("Game State UI")]
    public TMPro.TextMeshProUGUI phaseText;            // Texto para mostrar la fase actual
    public TMPro.TextMeshProUGUI damageText;           // Texto para mostrar el daño estructural
    public TMPro.TextMeshProUGUI currentAgentText;     // Texto para mostrar el agente actual
    public TMPro.TextMeshProUGUI remainingVictimsText; // Texto para mostrar víctimas restantes
    public TMPro.TextMeshProUGUI savedVictimsText;     // Texto para mostrar víctimas salvadas
    public TMPro.TextMeshProUGUI deadVictimsText;      // Texto para mostrar víctimas muertas
    [SerializeField] private GameObject gameOverPanel;  // Panel de UI para fin de juego
    [SerializeField] private TMPro.TextMeshProUGUI gameOverText;  // Texto para el mensaje de fin de juego
    private const int MAX_DAMAGE = 24;                  // Daño máximo permitido
    private const int TOTAL_VICTIMS = 15;               // Número total de víctimas
    private int savedVictims = 0;                      // Contador de víctimas salvadas
    private int deadVictims = 0;                       // Contador de víctimas muertas

    [Header("API")]
    public string stepUrl = "http://192.168.0.110:3690/api/step"; 
    [Header("Grid Reference")]

    public Vector3 firstCellPosition = new Vector3(27.98f, -0.005f, -1.29f);


    [Header("Grid Settings")]
    public int totalRows = 6;   // filas
    public int totalCols = 8;   // columnas
    public float cellSizeX = 1.7f; // ancho real de la celda
    public float cellSizeZ = 5f;   // profundidad real de la celda

    [Header("Prefabs")]
    public GameObject firePrefab;
    public GameObject agentPrefab; // 
    public Transform gridParent; 
    [Header("POI Prefabs")]
    public GameObject warningPrefab;      // Prefab para POIs no revelados
    public GameObject victimPrefab;       // Prefab para víctimas
    public GameObject falseAlarmPrefab;   // Prefab para falsas alarmas

    [Header("Smoke Prefab")]
    public GameObject smokePrefab;

    private readonly List<GameObject> activeFires = new List<GameObject>();
    private readonly List<GameObject> activeAgents = new List<GameObject>();
    private readonly List<GameObject> activePOIs = new List<GameObject>();
    private readonly List<GameObject> activeSmoke = new List<GameObject>();

    void Start()
    {
        if (firePrefab == null)
        {
            Debug.LogError("⚠️ FireManager: firePrefab no asignado en el Inspector.");
        }
        if (agentPrefab == null)
        {
            Debug.LogError("⚠️ FireManager: agentPrefab no asignado en el Inspector.");
        }
        if (smokePrefab == null)
        {
            Debug.LogError("⚠️ FireManager: smokePrefab no asignado en el Inspector.");
        }
        StartCoroutine(ResetAndStart()); // Reinicia el modelo antes de iniciar la simulación
    }

    IEnumerator ResetAndStart()
    {
        yield return StartCoroutine(ResetCoroutine());
        yield return new WaitForSeconds(0.5f); // Espera breve para asegurar el reset
        
        // Obtener el estado inicial del juego
        yield return StartCoroutine(GetGameState());
        
        StartCoroutine(StepCoroutine());
        yield return StartCoroutine(GetPOIs());
        yield return StartCoroutine(GetSmoke());
    }

    IEnumerator ResetCoroutine()
    {
        Debug.Log("Iniciando reinicio del modelo...");
        
        // Limpiar estado actual
        ClearFires();
        ClearAgents();
        ClearPOIs();
        ClearSmoke();
        
        savedVictims = 0;
        deadVictims = 0;
        
        using (UnityWebRequest www = UnityWebRequest.PostWwwForm("http://192.168.0.110:3690/api/reset", ""))
        {
            yield return www.SendWebRequest();
            
            if (www.result == UnityWebRequest.Result.Success)
            {
                Debug.Log("Modelo reiniciado correctamente.");
                
                // Reinicializar el estado del juego
                yield return StartCoroutine(GetGameState());
                yield return StartCoroutine(GetPOIs());
                yield return StartCoroutine(GetSmoke());
            }
            else
            {
                Debug.LogError($"Error al reiniciar el modelo: {www.error}");
                Debug.LogError($"Código de respuesta: {www.responseCode}");
                Debug.LogError($"Texto de respuesta: {www.downloadHandler.text}");
            }
        }
    }


    IEnumerator StepCoroutine()
    {
        while (true)
        {
            Debug.Log($"Intentando hacer POST a {stepUrl}");
            using (UnityWebRequest www = UnityWebRequest.PostWwwForm(stepUrl, ""))
            {
                yield return www.SendWebRequest();

                if (www.responseCode == 500)
                {
                    Debug.LogError($"Error 500 del servidor: {www.downloadHandler.text}");
                    yield return new WaitForSeconds(2f); // Esperar antes de reintentar
                    continue;
                }

                if (www.result == UnityWebRequest.Result.Success)
                {
                    string json = www.downloadHandler.text;
                    Debug.Log($"Respuesta del servidor: {json}");
                    StepResponse response = JsonUtility.FromJson<StepResponse>(json);

                    ClearFires();
                    foreach (FireData fire in response.fires)
                    {
                        Vector3 pos = GetCellPosition(fire.row, fire.col);
                        Vector3 originalScale = firePrefab.transform.localScale;
                        GameObject fireObj = Instantiate(firePrefab, pos, firePrefab.transform.rotation);
                        fireObj.transform.SetParent(gridParent, worldPositionStays: true);
                        fireObj.transform.localScale = originalScale;
                        activeFires.Add(fireObj);
                        
                        // Verificar si hay POIs en la casilla con fuego
                        StartCoroutine(CheckPOIInFire(fire.row, fire.col));
                    }
                    
                    // Actualizar el estado del juego
                    yield return StartCoroutine(GetGameState());
                    
                    // Actualizar el humo en cada paso
                    StartCoroutine(GetSmoke());

                    ClearAgents();
                    foreach (AgentData agent in response.agents)
                    {
                        Vector3 pos = GetCellPosition(agent.y, agent.x);
                        Vector3 originalScale = agentPrefab.transform.localScale;
                        GameObject agentObj = Instantiate(agentPrefab, pos, agentPrefab.transform.rotation);
                        agentObj.transform.SetParent(gridParent, worldPositionStays: true);
                        agentObj.transform.localScale = originalScale;
                        
                        // Agregar BoxCollider para detectar POIs si no existe
                        BoxCollider collider = agentObj.GetComponent<BoxCollider>();
                        if (collider == null)
                        {
                            collider = agentObj.AddComponent<BoxCollider>();
                            collider.isTrigger = true;
                            collider.size = new Vector3(1f, 1f, 1f); // Ajusta según necesites
                        }

                        // Configurar el color según el estado del agente
                        Renderer rend = agentObj.GetComponent<Renderer>();
                        if (rend != null)
                        {
                            if (agent.knocked_out)
                                rend.material.color = Color.gray;
                            else if (agent.isCarryingVictim)
                                rend.material.color = Color.green; // Color especial cuando lleva víctima
                            else
                                rend.material.color = Color.cyan; // Color por defecto para todos los agentes
                        }

                        // Agregar el script para manejar colisiones con POIs
                        AgentBehavior behavior = agentObj.AddComponent<AgentBehavior>();
                        behavior.Initialize(this, agent);

                        activeAgents.Add(agentObj);
                    }
                }
                else
                {
                    Debug.LogError($"Error en API step: {www.error}");
                    Debug.LogError($"Código de respuesta: {www.responseCode}");
                    Debug.LogError($"Texto de respuesta: {www.downloadHandler.text}");
                    
                    // Verificar si necesitamos reiniciar el modelo
                    if (www.responseCode == 500)
                    {
                        Debug.Log("Intentando reiniciar el modelo...");
                        yield return StartCoroutine(ResetCoroutine());
                        yield return new WaitForSeconds(1f);
                    }
                    else
                    {
                        yield return new WaitForSeconds(2f); // Esperar antes de reintentar
                    }
                }
            }
            yield return new WaitForSeconds(1f); // refresco cada segundo
        }
    }
IEnumerator GetPOIs()
{
    Debug.Log("Iniciando GetPOIs");
    using (UnityWebRequest www = UnityWebRequest.Get("http://192.168.0.110:3690/api/pois"))
    {
        yield return www.SendWebRequest();
        if (www.result == UnityWebRequest.Result.Success)
        {
            string json = www.downloadHandler.text;
            Debug.Log($"API POIs Response: {json}");
            POIResponse response = JsonUtility.FromJson<POIResponse>(json);
            Debug.Log($"Número de POIs recibidos: {response.pois.Length}");
            
            // Limpiar los POIs existentes
            foreach (GameObject poi in activePOIs)
            {
                Debug.Log($"Destruyendo POI en posición: {poi.transform.position}");
                Destroy(poi);
            }
            activePOIs.Clear();
            
            // Verificar prefabs
            if (warningPrefab == null) Debug.LogError("Warning Prefab no está asignado!");
            if (victimPrefab == null) Debug.LogError("Victim Prefab no está asignado!");
            if (falseAlarmPrefab == null) Debug.LogError("False Alarm Prefab no está asignado!");
            
            foreach (POIData poi in response.pois)
            {
                // Convertir coordenadas de Python a Unity
                var (row, col) = PythonToUnityCoords(poi.x, poi.y);
                Vector3 position = GetCellPosition(row, col);
                Debug.Log($"Procesando POI - Python: ({poi.x}, {poi.y}) -> Unity: (row={row}, col={col}), revelado: {poi.revealed}, tipo: {poi.type}");
                
                // Seleccionar el prefab adecuado según el estado del POI
                GameObject prefabToUse;
                string prefabDescription;
                
                if (!poi.revealed)
                {
                    prefabToUse = warningPrefab;
                    prefabDescription = "warning";
                    Debug.Log($"POI no revelado - Usando warning prefab para POI tipo: {poi.type}");
                }
                else
                {
                    if (poi.type == "victim")
                    {
                        prefabToUse = victimPrefab;
                        prefabDescription = "victim";
                        Debug.Log($"POI revelado - Usando victim prefab");
                    }
                    else
                    {
                        prefabToUse = falseAlarmPrefab;
                        prefabDescription = "false_alarm";
                        Debug.Log($"POI revelado - Usando false alarm prefab");
                    }
                }
                
                // Verificar que el prefab existe
                if (prefabToUse == null)
                {
                    Debug.LogError($"Prefab no asignado para POI tipo: {prefabDescription}");
                    continue;
                }
                
                Debug.Log($"Estado del POI - Posición: ({poi.x}, {poi.y}), Revelado: {poi.revealed}, Tipo: {poi.type}, Usando prefab: {prefabDescription}");

                // Instanciar el POI y configurarlo
                Debug.Log($"Intentando instanciar POI en posición: {position}");
                GameObject poiObject = Instantiate(prefabToUse, position, prefabToUse.transform.rotation);
                
                // Guardar la escala original del prefab
                Vector3 originalScale = prefabToUse.transform.localScale;
                
                if (gridParent != null)
                {
                    // Primero asignar el padre manteniendo la posición mundial
                    poiObject.transform.SetParent(gridParent, worldPositionStays: true);
                    
                    // Luego asegurar que la escala sea la correcta
                    poiObject.transform.localScale = originalScale;
                    
                    Debug.Log($"POI asignado al gridParent. Posición: {poiObject.transform.position}, " +
                            $"Rotación: {poiObject.transform.rotation.eulerAngles}, " +
                            $"Escala: {poiObject.transform.localScale}");
                }
                else
                {
                    Debug.LogWarning("gridParent es null!");
                }
                
                // Configurar el tag y collider
                poiObject.tag = "POI";
                
                if (poiObject.GetComponent<BoxCollider>() == null)
                {
                    BoxCollider collider = poiObject.AddComponent<BoxCollider>();
                    collider.isTrigger = true;
                }

                activePOIs.Add(poiObject);
            }
        }
        else
        {
            Debug.LogError("Error API POIs: " + www.error);
        }
    }
}

    IEnumerator GetSmoke()
    {
        using (UnityWebRequest www = UnityWebRequest.Get("http://192.168.0.110:3690/api/smoke"))
        {
            yield return www.SendWebRequest();
            if (www.result == UnityWebRequest.Result.Success)
            {
                string json = www.downloadHandler.text;
                Debug.Log("Respuesta API Smoke: " + json);  // Debug para ver la respuesta
                
                SmokeResponse response = JsonUtility.FromJson<SmokeResponse>(json);
                ClearSmoke();
                
                if (response.smoke != null && response.smoke.Length > 0)
                {
                    Debug.Log($"Procesando {response.smoke.Length} celdas con humo");
                    foreach (SmokeData smoke in response.smoke)
                    {
                        Vector3 pos = GetCellPosition(smoke.row, smoke.col);
                        pos.y += 0.5f;  // Elevar el humo un poco sobre el suelo
                        Vector3 originalScale = smokePrefab.transform.localScale;
                        GameObject smokeObj = Instantiate(smokePrefab, pos, smokePrefab.transform.rotation);
                        smokeObj.transform.SetParent(gridParent, worldPositionStays: true);
                        smokeObj.transform.localScale = originalScale;
                        activeSmoke.Add(smokeObj);
                        Debug.Log($"Humo creado en posición: {pos}");
                    }
                }
                else
                {
                    Debug.Log("No hay humo para mostrar");
                }
            }
            else
            {
                Debug.LogError("Error API Smokeee: " + www.error); 
            }
        }
    }

    private IEnumerator GetGameState()
    {
        using (UnityWebRequest www = UnityWebRequest.Get("http://192.168.0.110:3690/api/gamestate"))
        {
            yield return www.SendWebRequest();
            if (www.result == UnityWebRequest.Result.Success)
            {
                string json = www.downloadHandler.text;
                GameStateResponse response = JsonUtility.FromJson<GameStateResponse>(json);
                UpdateGameStateUI(response.gameState);
                
                // Verificar fin del juego
                if (response.gameState.gameOver)
                {
                    ShowGameOverScreen(response.gameState.gameWon, response.gameState.endReason);
                }
            }
            else
            {
                Debug.LogError("Error API GameState: " + www.error);
            }
        }
    }

    private void UpdateGameStateUI(GameStateData gameState)
    {
        Debug.Log($"Actualizando UI - Fase: {gameState.phase}, Daño: {gameState.damageCount}, Agente: {gameState.currentAgent}");
        
        if (phaseText != null)
        {
            phaseText.text = $"Turno: {gameState.phase}";
            Debug.Log($"Phase Text actualizado: {phaseText.text}");
        }
        else
        {
            Debug.LogError("Phase Text no está asignado en el Inspector");
        }
        
        if (damageText != null)
        {
            damageText.text = $"Daño: {gameState.damageCount}/{MAX_DAMAGE}";
            Debug.Log($"Damage Text actualizado: {damageText.text}");
        }
        else
        {
            Debug.LogError("Damage Text no está asignado en el Inspector");
        }
        
        if (currentAgentText != null)
        {
            currentAgentText.text = $"Agente Actual: {gameState.currentAgent}";
            Debug.Log($"Current Agent Text actualizado: {currentAgentText.text}");
        }
        else if (currentAgentText == null)
        {
            Debug.LogError("Current Agent Text no está asignado en el Inspector");
        }

        // Actualizar contadores de víctimas
        int remainingVictims = TOTAL_VICTIMS - (savedVictims + deadVictims);
        
        if (remainingVictimsText != null)
        {
            remainingVictimsText.text = $"Victims: {remainingVictims}";
        }
        
        if (savedVictimsText != null)
        {
            savedVictimsText.text = $"Saved: {savedVictims}";
        }
        
        if (deadVictimsText != null)
        {
            deadVictimsText.text = $"Dead: {deadVictims}";
        }
    }

    private void ShowGameOverScreen(bool victory, string reason)
    {
        if (gameOverPanel != null)
        {
            gameOverPanel.SetActive(true);
            if (gameOverText != null)
            {
                string result = victory ? "¡VICTORIA!" : "DERROTA";
                gameOverText.text = $"{result}\n{reason}";
            }
        }
    }

    public IEnumerator RevealPOI(int row, int col)
    {
        // Convertir coordenadas de Unity a Python
        var (x, y) = UnityToPythonCoords(row, col);
        Debug.Log($"Intentando revelar POI - Unity: (row={row}, col={col}) -> Python: (x={x}, y={y})");
        WWWForm form = new WWWForm();
        form.AddField("x", x);
        form.AddField("y", y);

        using (UnityWebRequest www = UnityWebRequest.Post("http://192.168.0.110:3690/api/reveal_poi", form))
        {
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.Success)
            {
                string json = www.downloadHandler.text;
                Debug.Log($"Respuesta del servidor para revelar POI: {json}");
                RevealPOIResponse response = JsonUtility.FromJson<RevealPOIResponse>(json);

                if (response.success)
                {
                    if (response.poiType == "victim")
                    {
                        Debug.Log("¡Víctima encontrada!");
                        savedVictims++;
                        UpdateGameStateUI(new GameStateData()); // Actualizar UI
                    }
                    else if (response.poiType == "false_alarm")
                    {
                        Debug.Log("Falsa alarma encontrada");
                    }
                    
                    // Actualizar visualización de POIs siempre que sea exitoso
                    Debug.Log("Actualizando visualización de POIs después de revelar");
                    yield return StartCoroutine(GetPOIs());
                }
                else
                {
                    Debug.LogWarning("No se pudo revelar el POI: " + response.message);
                }
            }
            else
            {
                Debug.LogError("Error al revelar POI: " + www.error);
            }
        }
    }

    void ClearFires()
    {
        foreach (GameObject fire in activeFires)
        {
            Destroy(fire);
        }
        activeFires.Clear();
    }

    void ClearAgents()
    {
        foreach (GameObject agent in activeAgents)
        {
            Destroy(agent);
        }
        activeAgents.Clear();
    }

// Convierte de coordenadas de Unity a Python
private (int x, int y) UnityToPythonCoords(int row, int col)
{
    return (totalCols - 1 - col, row);
}


private (int row, int col) PythonToUnityCoords(int x, int y)
{
    return (y, totalCols - 1 - x);
}

Vector3 GetCellPosition(int row, int col)
{
    float x = firstCellPosition.x + (totalCols - 1 - col) * cellSizeX + cellSizeX / 2f;
    float z = firstCellPosition.z + row * cellSizeZ + cellSizeZ / 2f;
    float y = firstCellPosition.y;
    return new Vector3(x, y, z);
}



    void OnDrawGizmos()
    {
        if (gridParent == null) return;

        Gizmos.color = Color.gray;

       for (int row = 0; row < totalRows; row++)
        {
            for (int col = 0; col < totalCols; col++)
            {
                Vector3 pos = GetCellPosition(row, col);
                Gizmos.DrawWireCube(pos, new Vector3(cellSizeX, 0.01f, cellSizeZ));
            }
        }
    }
    void ClearPOIs()
    {
        foreach (GameObject poi in activePOIs)
        {
            Destroy(poi);
        }
        activePOIs.Clear();
    }

    void ClearSmoke()
    {
        foreach (GameObject smoke in activeSmoke)
        {
            Destroy(smoke);
        }
        activeSmoke.Clear();
    }

    private IEnumerator CheckPOIInFire(int row, int col)
    {
        // Convertir coordenadas de Unity a Python
        var (x, y) = UnityToPythonCoords(row, col);
        Debug.Log($"Verificando POI en fuego - Unity: (row={row}, col={col}) -> Python: (x={x}, y={y})");
        using (UnityWebRequest www = UnityWebRequest.Get($"http://192.168.0.110:3690/api/check_poi_in_fire?x={x}&y={y}"))
        {
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.Success)
            {
                string json = www.downloadHandler.text;
                Debug.Log($"Respuesta del servidor para POI en fuego: {json}");
                RevealPOIResponse response = JsonUtility.FromJson<RevealPOIResponse>(json);

                if (response.success && !response.wasRevealed) // Solo si el POI no estaba revelado previamente
                {
                    Debug.Log($"POI encontrado en fuego - Tipo: {response.poiType}, Previamente revelado: {response.wasRevealed}");
                    
                    if (response.poiType == "victim")
                    {
                        Debug.Log("¡Víctima muerta por fuego!");
                        deadVictims++;
                        Debug.Log($"Total de víctimas muertas: {deadVictims}");
                        UpdateGameStateUI(new GameStateData()); // Actualizar UI con nuevo contador
                    }
                    else
                    {
                        Debug.Log("Falsa alarma revelada por fuego");
                    }
                    
                    // Esperar un momento para asegurar que el servidor procesó el cambio
                    yield return new WaitForSeconds(0.1f);
                    
                    // Actualizar visualización de POIs
                    Debug.Log("Actualizando visualización de POIs después de fuego");
                    yield return StartCoroutine(GetPOIs());
                }
            }
            else
            {
                Debug.LogError("Error al verificar POI en fuego: " + www.error);
            }
        }
    }
}
