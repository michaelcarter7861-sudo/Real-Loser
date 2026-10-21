using UnityEngine;
using UnityEngine.UI;
using UnityEngine.SceneManagement;
using UnityEngine.EventSystems;

namespace RealLoserStudio.Tactical.UI
{
    /// <summary>Pause overlay with practical audio, look-sensitivity and quality controls.</summary>
    public class TacticalPauseSettings : MonoBehaviour
    {
        Canvas canvas;
        GameObject panel;
        bool isOpen;
        bool settingsOpen;
        float oldTimeScale = 1f;

        void Update()
        {
            if (Input.GetKeyDown(KeyCode.Escape) || Input.GetKeyDown(KeyCode.JoystickButton7) ||
                (Application.platform == RuntimePlatform.Android && Input.GetKeyDown(KeyCode.Backspace)))
            {
                if (settingsOpen) { settingsOpen=false; ShowPause(); }
                else if (isOpen) Resume();
                else ShowPause();
            }
        }
        void EnsureCanvas()
        {
            if (canvas != null) return;
            if (FindObjectOfType<EventSystem>() == null) {
                GameObject es = new GameObject("PauseMenuEventSystem");
                es.AddComponent<EventSystem>(); es.AddComponent<StandaloneInputModule>();
            }
            GameObject c = new GameObject("TacticalPauseCanvas");
            canvas = c.AddComponent<Canvas>(); canvas.renderMode=RenderMode.ScreenSpaceOverlay; canvas.sortingOrder=300;
            CanvasScaler scaler=c.AddComponent<CanvasScaler>(); scaler.uiScaleMode=CanvasScaler.ScaleMode.ScaleWithScreenSize; scaler.referenceResolution=new Vector2(1920,1080);
            c.AddComponent<GraphicRaycaster>();
        }
        public void ShowPause()
        {
            EnsureCanvas();
            if(panel!=null) Destroy(panel);
            panel=MakePanel(canvas.transform,"PausePanel",new Vector2(.28f,.12f),new Vector2(.72f,.88f),new Color(.025f,.04f,.045f,.97f));
            Label(panel.transform,"Title",settingsOpen?"FIELD SETTINGS":"MISSION PAUSED",new Vector2(.06f,.84f),new Vector2(.94f,.97f),34);
            if(settingsOpen) BuildSettings();
            else {
                Button(panel.transform,"Resume Mission",new Vector2(.18f,.64f),new Vector2(.82f,.78f),Resume);
                Button(panel.transform,"Settings",new Vector2(.18f,.47f),new Vector2(.82f,.61f),OpenSettings);
                Button(panel.transform,"Restart Mission",new Vector2(.18f,.30f),new Vector2(.82f,.44f),Restart);
                Button(panel.transform,"Return to Command",new Vector2(.18f,.13f),new Vector2(.82f,.27f),ReturnToMenu);
            }
            isOpen=true; Time.timeScale=0f;
        }
        void BuildSettings()
        {
            Text volumeLabel=Label(panel.transform,"VolumeLabel","MASTER VOLUME",new Vector2(.10f,.68f),new Vector2(.50f,.78f),19);
            Slider volume=MakeSlider(panel.transform,new Vector2(.50f,.69f),new Vector2(.88f,.76f),AudioListener.volume);
            volume.onValueChanged.AddListener(v=>AudioListener.volume=v);
            Label(panel.transform,"QualityLabel","GRAPHICS QUALITY",new Vector2(.10f,.52f),new Vector2(.50f,.62f),19);
            Button(panel.transform,"Cycle Quality: "+QualitySettings.names[QualitySettings.GetQualityLevel()],new Vector2(.50f,.51f),new Vector2(.88f,.62f),CycleQuality);
            Label(panel.transform,"SensitivityLabel","LOOK SENSITIVITY",new Vector2(.10f,.36f),new Vector2(.50f,.46f),19);
            Slider sensitivity=MakeSlider(panel.transform,new Vector2(.50f,.37f),new Vector2(.88f,.44f),PlayerPrefs.GetFloat("PRL_LookSensitivity",1f)/2f);
            sensitivity.onValueChanged.AddListener(v=>PlayerPrefs.SetFloat("PRL_LookSensitivity",Mathf.Lerp(.25f,2f,v)));
            Button(panel.transform,"Back",new Vector2(.30f,.12f),new Vector2(.70f,.25f),BackToPause);
        }
        void BackToPause(){settingsOpen=false;ShowPause();}
        void OpenSettings(){settingsOpen=true;ShowPause();}
        void CycleQuality(){int next=(QualitySettings.GetQualityLevel()+1)%QualitySettings.names.Length;QualitySettings.SetQualityLevel(next,true);ShowPause();}
        void Resume(){if(panel!=null)Destroy(panel);settingsOpen=false;isOpen=false;Time.timeScale=1f;}
        void Restart(){Time.timeScale=1f;SceneManager.LoadScene(SceneManager.GetActiveScene().name);}
        void ReturnToMenu(){Time.timeScale=1f;SceneManager.LoadScene("MainMenu");}
        GameObject MakePanel(Transform parent,string name,Vector2 min,Vector2 max,Color color){
            GameObject g=new GameObject(name);g.transform.SetParent(parent,false);RectTransform r=g.AddComponent<RectTransform>();r.anchorMin=min;r.anchorMax=max;r.offsetMin=Vector2.zero;r.offsetMax=Vector2.zero;
            Image im=g.AddComponent<Image>();im.color=color;return g;
        }
        Text Label(Transform p,string n,string value,Vector2 min,Vector2 max,int size){
            GameObject g=MakePanel(p,n,min,max,new Color(0,0,0,0));Text t=g.AddComponent<Text>();t.font=Resources.GetBuiltinResource<Font>("Arial.ttf");t.text=value;t.fontSize=size;t.color=Color.white;t.alignment=TextAnchor.MiddleCenter;return t;
        }
        void Button(Transform p,string text,Vector2 min,Vector2 max,UnityEngine.Events.UnityAction action){
            GameObject g=MakePanel(p,"Button_"+text,min,max,new Color(.13f,.32f,.24f,1));Button b=g.AddComponent<Button>();b.onClick.AddListener(action);Label(g.transform,"Text",text,Vector2.zero,Vector2.one,20);
        }
        Slider MakeSlider(Transform p,Vector2 min,Vector2 max,float value){
            GameObject g=MakePanel(p,"Slider",min,max,new Color(.12f,.16f,.16f,1));Slider s=g.AddComponent<Slider>();s.minValue=0;s.maxValue=1;s.value=value;
            GameObject fill=MakePanel(g.transform,"Fill",Vector2.zero,new Vector2(value,1),new Color(.25f,.72f,.42f,1));
            s.fillRect=fill.GetComponent<RectTransform>();
            GameObject handle=MakePanel(g.transform,"Handle",new Vector2(value,0),new Vector2(value,1),Color.white);s.handleRect=handle.GetComponent<RectTransform>();
            return s;
        }
    }
}
