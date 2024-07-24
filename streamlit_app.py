import openai
import streamlit as st
from io import BytesIO
import base64
import numpy as np
from streamlit.components.v1 import html

# Initialize OpenAI client
client = openai.Client(api_key=st.secrets.get("OPENAI_API_KEY"))

# Load the password from Streamlit secrets
APP_PASSWORD = st.secrets.get("APP_PASSWORD")

# Check if the API key is available
if not client.api_key:
    st.warning("Por favor, insira sua chave API OpenAI para continuar.")
    st.stop()

# Check if the user is logged in
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Function to transcribe audio using Whisper API
def transcribe_audio(audio_file):
    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        return transcript.text
    except Exception as e:
        st.error(f"Erro na transcrição: {str(e)}")
        return None
    
# Function to analyze image using OpenAI API
def analyze_image(image_file):
    try:
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this medical image and provide a detailed description."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(image_file.getvalue()).decode()}"}}
                    ],
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Erro na análise da imagem: {str(e)}")
        return None

# Function to display the login page
def login_page():
    st.markdown("<h1 style='color: purple;'>Asclepius Login</h1>", unsafe_allow_html=True)
    password = st.text_input("Digite a senha:", type="password")
    if st.button("Login"):
        if password == APP_PASSWORD:
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.error("Senha incorreta. Por favor, tente novamente.")

# Function to display the main content
def main_page():
    # Content for instruction files in Portuguese
    system_01_intake = """
    # MISSÃO
    Você é um chatbot de recepção de dados de paciente focado em sintomas, os dados serão fornecidos pelo médico. Sua missão é fazer perguntas para ajudar o médico e auxiliar a articular completamente a consulta de maneira clara. Sua transcrição de chat será, em última instância, traduzida em notas de prontuário.

    # REGRAS
    Faça apenas uma pergunta de cada vez. Forneça algum contexto ou esclarecimento em torno das perguntas de acompanhamento que você faz. Não converse com o médico.
    """

    system_02_prepare_notes = """
    # MISSÃO
    Você é um bot de registro que receberá uma transcrição de recepção de dados do paciente. Você deve traduzir o registro do chat em notas médicas detalhadas para o médico.

    # ESQUEMA DE INTERAÇÃO
    O USUÁRIO lhe fornecerá a transcrição. Seu resultado será uma lista de notas hifenizadas. Certifique-se de capturar os sintomas e qualquer informação relevante de maneira ordenada e estruturada.
    """

    system_03_diagnosis = """
    # MISSÃO
    Você é um bot de notas médicas que receberá um prontuário ou sintomas de um paciente logo após a recepção. Você gerará uma lista dos diagnósticos mais prováveis ou vias de investigação para o médico seguir.

    # ESQUEMA DE INTERAÇÃO
    O USUÁRIO lhe fornecerá as notas médicas. Você gerará um relatório com o seguinte formato:

    # FORMATO DO RELATÓRIO

    1. <DIAGNÓSTICO POTENCIAL EM LETRAS MAIÚSCULAS>: <Descrição da condição, nomes alternativos comuns, etc>
       - DIFERENCIAIS: <Descrição dos diferenciais>
       - DEMOGRAFIA: <Demografia típica de afecção, fatores de risco demográficos>
       - SINTOMAS: <Lista formal de sintomas>
       - INDICADORES: <Por que este paciente corresponde a este diagnóstico>
       - CONTRAINDICADORES: <Por que este paciente não corresponde a este diagnóstico>
       - PROGNÓSTICO: <Perspectiva geral da condição>
       - TRATAMENTO: <Opções de tratamento disponíveis>
       - TESTES: <Testes de acompanhamento recomendados e o que você está procurando, informações probativas desejadas>

    2. <DIAGNÓSTICO POTENCIAL EM LETRAS MAIÚSCULAS>: <Descrição da condição, nomes alternativos comuns, etc>
       - DIFERENCIAIS: <Descrição dos diferenciais>
       - DEMOGRAFIA: <Demografia típica de afecção, fatores de risco demográficos>
       - SINTOMAS: <Lista formal de sintomas>
       - INDICADORES: <Por que este paciente corresponde a este diagnóstico>
       - CONTRAINDICADORES: <Por que este paciente não corresponde a este diagnóstico>
       - PROGNÓSTICO: <Perspectiva geral da condição>
       - TRATAMENTO: <Opções de tratamento disponíveis>
       - TESTES: <Testes de acompanhamento recomendados e o que você está procurando, informações probativas desejadas>
    """

    system_04_clinical = """
    # MISSÃO
    Você é um bot de recepção médica. Você está se preparando para a etapa final antes que o profissional médico (médico, enfermeiro, PA) avalie o paciente em um ambiente clínico. Você receberá notas da recepção do paciente, bem como vias de investigação diagnóstica geradas pelo sistema. Você deve preparar algumas recomendações clínicas para avaliar o paciente. Lembre-se de que esta é uma visita de cuidados primários.

    # SENTIDOS
    Visão, audição, olfato, tato (palpação) e outros testes clínicos. Quais sentidos o profissional médico deve estar atento? Dadas as notas, seja específico e probativo em suas recomendações. Certifique-se de explicar o que procurar, bem como por que isso pode ser útil.

    # EXAME CLÍNICO
    Liste técnicas específicas de exame que você recomenda, bem como o que procurar e por que. Lembre-se de que isso é estritamente para a visita clínica. Nos preocuparemos com encaminhamentos e acompanhamento mais tarde. Concentre-se apenas em técnicas de cuidados primários.

    # PERGUNTAS DE ENTREVISTA
    Sugira várias perguntas para o clínico fazer ao paciente como parte da investigação.

    # FORMATO DE SAÍDA
    Independentemente do formato de entrada (você pode receber notas, prontuários, registros de chat, etc.), seu formato de saída deve ser consistente e usar o seguinte:

    ## SENTIDOS

    VISÃO: <O que procurar ao envolver-se visualmente com o paciente. Explique por que esta informação pode ser probativa.>

    AUDIÇÃO: <O que ouvir ao envolver-se com o paciente. Explique por que esta informação pode ser probativa.>

    TATO: <Quais sensações físicas, se houver, procurar ao palpar. Explique por que esta informação pode ser probativa.>

    OLFATO: <Quais cheiros prestar atenção, se houver algum relevante. Explique por que esta informação pode ser probativa.>

    ## EXAME

    - <TÉCNICA DE EXAME EM LETRAS MAIÚSCULAS>: <Descrição do que procurar e por que, por exemplo, como este exame é probativo>
    - <TÉCNICA DE EXAME EM LETRAS MAIÚSCULAS>: <Descrição do que procurar e por que, por exemplo, como este exame é probativo>
    - <TÉCNICA DE EXAME EM LETRAS MAIÚSCULAS>: <Descrição do que procurar e por que, por exemplo, como este exame é probativo>

    ## ENTREVISTA

    - <PROPÓSITO PROBATIVO DA PERGUNTA EM LETRAS MAIÚSCULAS>: "<Pergunta sugerida>?"
    - <PROPÓSITO PROBATIVO DA PERGUNTA EM LETRAS MAIÚSCULAS>: "<Pergunta sugerida>?"
    - <PROPÓSITO PROBATIVO DA PERGUNTA EM LETRAS MAIÚSCULAS>: "<Pergunta sugerida>?"
    """

    system_05_referrals = """
    # MISSÃO
    Você é um bot clínico médico. Você receberá notas médicas, prontuários ou outros registros do paciente ou do clínico. Seu trabalho principal é recomendar encaminhamentos para especialistas e/ou testes de acompanhamento.

    # FORMATO DO RELATÓRIO
    Seu relatório deve seguir este formato:

    ## ENCAMINHAMENTOS

    - <TIPO DE ESPECIALISTA EM LETRAS MAIÚSCULAS>: <Descrição do trabalho, recomendações, testes e comunicação a ser enviada para este especialista, por exemplo, o que estão procurando e por quê>
    - <TIPO DE ESPECIALISTA EM LETRAS MAIÚSCULAS>: <Descrição do trabalho, recomendações, testes e comunicação a ser enviada para este especialista, por exemplo, o que estão procurando e por quê>

    ## EXAMES E TESTES

    - <TIPO DE EXAME OU TRABALHO DE LABORATÓRIO>: <Descrição do trabalho a ser feito, por exemplo, imagem, flebotomia, etc., bem como valor probativo, por exemplo, indicações, contraindicações, diferenciais, em outras palavras, o que você está tentando confirmar ou descartar>
    - <TIPO DE EXAME OU TRABALHO DE LABORATÓRIO>: <Descrição do trabalho a ser feito, por exemplo, imagem, flebotomia, etc., bem como valor probativo, por exemplo, indicações, contraindicações, diferenciais, em outras palavras, o que você está tentando confirmar ou descartar>
    """

    system_06_conduct = """
    # MISSÃO
    Você é um bot de conduta médica. Sua tarefa é sugerir uma conduta médica baseada em todas as informações anteriores dos sistemas de recepção, notas médicas, diagnóstico, avaliação clínica e encaminhamentos.

    # ESQUEMA DE INTERAÇÃO
    O USUÁRIO lhe fornecerá todas as notas médicas e relatórios anteriores. Sua saída deve ser uma lista detalhada de condutas médicas recomendadas para o paciente, considerando o diagnóstico, avaliação clínica e encaminhamentos.

    # FORMATO DO RELATÓRIO

    1. <NOME DA CONDUTA EM LETRAS MAIÚSCULAS>: <Descrição detalhada da conduta recomendada>
       - MOTIVAÇÃO: <Razão pela qual esta conduta é recomendada>
       - OBJETIVOS: <Objetivos específicos desta conduta>
       - PROCEDIMENTOS: <Procedimentos a serem seguidos>
       - MONITORAMENTO: <Métodos de monitoramento e avaliação da eficácia da conduta>
       - AJUSTES: <Possíveis ajustes na conduta baseada na resposta do paciente>

    2. <NOME DA CONDUTA EM LETRAS MAIÚSCULAS>: <Descrição detalhada da conduta recomendada>
       - MOTIVAÇÃO: <Razão pela qual esta conduta é recomendada>
       - OBJETIVOS: <Objetivos específicos desta conduta>
       - PROCEDIMENTOS: <Procedimentos a serem seguidos>
       - MONITORAMENTO: <Métodos de monitoramento e avaliação da eficácia da conduta>
       - AJUSTES: <Possíveis ajustes na conduta baseada na resposta do paciente>
    """
    system_07_prescription = """
    # MISSÃO
    Você é um bot de prescrição médica. Sua tarefa é gerar uma prescrição médica com base nos principais sintomas e diagnósticos prováveis fornecidos.

    # ESQUEMA DE INTERAÇÃO
    O USUÁRIO lhe fornecerá as informações sobre os sintomas principais e diagnósticos prováveis. Sua saída deve ser uma prescrição médica detalhada.

    # FORMATO DO RELATÓRIO

    PRESCRIÇÃO MÉDICA

    Data: <Data atual>

    Nome do Paciente: <Nome do paciente, se fornecido>

    1. <NOME DO MEDICAMENTO>
       - Dosagem: <Dosagem recomendada>
       - Frequência: <Frequência de administração>
       - Duração: <Duração do tratamento>
       - Instruções especiais: <Quaisquer instruções específicas para a administração>

    2. <NOME DO MEDICAMENTO>
       - Dosagem: <Dosagem recomendada>
       - Frequência: <Frequência de administração>
       - Duração: <Duração do tratamento>
       - Instruções especiais: <Quaisquer instruções específicas para a administração>

    RECOMENDAÇÕES ADICIONAIS:
    - <Qualquer recomendação adicional ou cuidados especiais>
"""

    # Initialize session state
    if "conversation" not in st.session_state:
        st.session_state.conversation = [{'role': 'system', 'content': system_01_intake}]

    if "user_messages" not in st.session_state:
        st.session_state.user_messages = []

    if "all_messages" not in st.session_state:
        st.session_state.all_messages = []

    if "transcription" not in st.session_state:
        st.session_state.transcription = ""

    if "image_analysis" not in st.session_state:
        st.session_state.image_analysis = []

    # Function for the live audio recording
    st.title("Live Audio Recording")

    # JavaScript code for audio recording
    js_code = """
    <script>
    let mediaRecorder;
    let audioChunks = [];

    function startRecording() {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.start();

                mediaRecorder.addEventListener("dataavailable", event => {
                    audioChunks.push(event.data);
                });

                mediaRecorder.addEventListener("stop", () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    const audioUrl = URL.createObjectURL(audioBlob);
                    const audio = new Audio(audioUrl);
                    audio.play();
                    sendData(audioBlob);
                });

                document.getElementById("start").disabled = true;
                document.getElementById("stop").disabled = false;
            });
    }

    function stopRecording() {
        mediaRecorder.stop();
        document.getElementById("start").disabled = false;
        document.getElementById("stop").disabled = true;
    }

    function sendData(audioBlob) {
        const reader = new FileReader();
        reader.onload = function(event) {
            const base64data = event.target.result.split(',')[1];
            fetch('/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ audio_data: base64data })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.parent.postMessage({type: 'audioRecorded'}, '*');
                }
            });
        };
        reader.readAsDataURL(audioBlob);
    }
    </script>

    <button id="start" onclick="startRecording()">Start Recording</button>
    <button id="stop" onclick="stopRecording()" disabled>Stop Recording</button>
    """

    # Display the HTML and JavaScript code
    html(js_code, height=100)

    # Check if audio data has been received
    if 'audio_data' in st.session_state:
        st.audio(st.session_state.audio_data, format='audio/wav')
        if st.button("Transcribe Audio"):
            transcription = transcribe_audio(st.session_state.audio_data)
            if transcription:
                st.write("Transcription:", transcription)
                st.session_state.transcription = transcription
                st.session_state.all_messages.append(f'TRANSCRIPTION: {transcription}')

    # Handle the POST request with audio data
    if st.button("Process Recorded Audio"):
        audio_data = st.session_state.get('_json_data', {}).get('audio_data', '')
        if audio_data:
            audio_bytes = base64.b64decode(audio_data)
            st.session_state.audio_data = audio_bytes
            st.experimental_rerun()

    # Function to call OpenAI API
    def chatbot(conversation, model="gpt-4o-mini", temperature=0, max_tokens=3000):
        response = client.chat.completions.create(
            model=model, 
            messages=conversation, 
            temperature=temperature, 
            max_tokens=max_tokens
        )
        text = response.choices[0].message.content
        return text

    # Chatbot interaction
    st.markdown("<h1 style='color: purple;'>Asclepius</h1>", unsafe_allow_html=True)

# Audio recording and transcription
    st.header("Audio Recording and Transcription")
    audio_file = st.file_uploader("Upload an audio file", type=["wav", "mp3", "m4a"])
    if audio_file is not None:
        st.audio(audio_file, format="audio/wav")
        if st.button("Transcribe Audio"):
            transcription = transcribe_audio(audio_file)
            if transcription:
                st.session_state.transcription = transcription
                st.write("Transcription:", transcription)
                st.session_state.all_messages.append(f'TRANSCRIPTION: {transcription}')

    # Image upload and analysis
    st.header("Image Upload and Analysis")
    image_file = st.file_uploader("Upload a medical image", type=["jpg", "jpeg", "png"])
    if image_file is not None:
        st.image(image_file, caption="Uploaded Image", use_column_width=True)
        if st.button("Analyze Image"):
            image_analysis = analyze_image(image_file)
            if image_analysis:
                st.session_state.image_analysis.append(image_analysis)
                st.write("Image Analysis:", image_analysis)
                st.session_state.all_messages.append(f'IMAGE ANALYSIS: {image_analysis}')

    st.header("Descreva o caso clínico. Digite PRONTO quando terminar.")
    if prompt := st.text_area("Luis:", height=200):
        if prompt.strip().upper() != "PRONTO" and prompt.strip().upper() != "PRESCRIPTION":
            st.session_state.user_messages.append(prompt)
            st.session_state.all_messages.append(f'Luis: {prompt}')
            st.session_state.conversation.append({'role': 'user', 'content': prompt})

            response = chatbot(st.session_state.conversation)
            st.session_state.conversation.append({'role': 'assistant', 'content': response})
            st.session_state.all_messages.append(f'RECEPÇÃO: {response}')
            st.write(f'**RECEPÇÃO:** {response}')
        elif prompt.strip().upper() == "PRONTO":
            st.write("Consegui os dados. Gerando notas e relatórios...")

            # Include transcription and image analysis in the notes
            all_input = '\n\n'.join(st.session_state.all_messages)
            if st.session_state.transcription:
                all_input += f"\n\nAudio Transcription:\n{st.session_state.transcription}"
            if st.session_state.image_analysis:
                all_input += f"\n\nImage Analysis:\n" + "\n".join(st.session_state.image_analysis)

            # Generate Intake Notes
            st.write("**Gerando Notas de Recepção...**")
            notes_conversation = [{'role': 'system', 'content': system_02_prepare_notes}]
            notes_conversation.append({'role': 'user', 'content': all_input})
            notes = chatbot(notes_conversation)
            st.write(f'**Versão das notas da conversa:**\n\n{notes}')

            # Generate Hypothesis Report
            st.write("**Gerando Relatório de Hipóteses...**")
            report_conversation = [{'role': 'system', 'content': system_03_diagnosis}]
            report_conversation.append({'role': 'user', 'content': notes})
            report = chatbot(report_conversation)
            st.write(f'**Relatório de Hipóteses:**\n\n{report}')

            # Prepare for Clinical Evaluation
            st.write("**Preparando para Avaliação Clínica...**")
            clinical_conversation = [{'role': 'system', 'content': system_04_clinical}]
            clinical_conversation.append({'role': 'user', 'content': notes})
            clinical = chatbot(clinical_conversation)
            st.write(f'**Avaliação Clínica:**\n\n{clinical}')

            # Generate Referrals and Tests
            st.write("**Gerando Encaminhamentos e Exames Complementares...**")
            referrals_conversation = [{'role': 'system', 'content': system_05_referrals}]
            referrals_conversation.append({'role': 'user', 'content': notes})
            referrals = chatbot(referrals_conversation)
            st.write(f'**Encaminhamentos e Exames Complementares:**\n\n{referrals}')

            # Generate Suggested Medical Conduct
            st.write("**Gerando Conduta Médica Sugerida...**")
            conduct_conversation = [{'role': 'system', 'content': system_06_conduct}]
            conduct_conversation.append({'role': 'user', 'content': notes})
            conduct = chatbot(conduct_conversation)
            st.write(f'**Conduta Médica Sugerida:**\n\n{conduct}')

        elif prompt.strip().upper() == "PRESCRIPTION":
            st.write("Gerando prescrição médica...")

            # Generate Prescription
            prescription_conversation = [{'role': 'system', 'content': system_07_prescription}]
            prescription_conversation.append({'role': 'user', 'content': f"Symptoms and probable diagnosis:\n{report}"})
            prescription = chatbot(prescription_conversation)
            st.write(f'**Prescrição Médica:**\n\n{prescription}')

# Main Execution Flow
if st.session_state.logged_in:
    main_page()
else:
    login_page()
