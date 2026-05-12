import logging
import asyncio
from aiogram import Router, F, types
from aiogram.exceptions import TelegramAPIError
from core.agent_graph import processar_mensagem_telegram

logger = logging.getLogger(__name__)

# Roteador dedicado às mensagens em linguagem natural
router = Router(name="natural_language")

async def process_langgraph_task(bot, chat_id: int, message_id: int, user_text: str):
    """
    Task de background projetada para blindar a infraestrutura contra timeouts.
    Executa toda a cadeia computacional do LangGraph e substitui a mensagem
    provisória pela resposta rica quando finalizada.
    """
    typing_task = None
    try:
        # Função auxiliar para manter o 'typing' persistente. O Telegram expira o 'typing'
        # após ~5 segundos, então renovamos a cada 4 segundos no Event Loop.
        async def keep_typing():
            try:
                while True:
                    await bot.send_chat_action(chat_id=chat_id, action="typing")
                    await asyncio.sleep(4)
            except asyncio.CancelledError:
                pass
                
        typing_task = asyncio.create_task(keep_typing())

        logger.info(f"Processando matriz LangGraph em background para o chat_id {chat_id}...")
        
        # Invoca o grafo via entrypoint oficial (Agentic LangGraph)
        reply_message = await processar_mensagem_telegram(mensagem=user_text, chat_id=str(chat_id))
        
        # Interrompe a animação de digitação
        typing_task.cancel()
        
        # Magia do "Acknowledge & Update": edita o texto do balão provisório e exibe o veredito
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=reply_message
        )
        logger.info(f"Resposta final editada com sucesso no chat_id {chat_id}.")
        
    except asyncio.CancelledError:
        logger.warning(f"A execução background para o chat {chat_id} foi abortada.")
    except Exception as e:
        logger.error(f"Falha catastrófica no workflow assíncrono: {e}", exc_info=True)
        
        if typing_task:
            typing_task.cancel()
            
        # Tratamento de segurança: avisa elegantemente que ocorreu pane técnica
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="⚠️ *Aviso do Sistema:* Perda de conexão com os radares de inteligência. A análise não pôde ser completada no momento.",
                parse_mode="Markdown"
            )
        except TelegramAPIError as ex:
            logger.error(f"Incapacidade absoluta de editar a mensagem de erro (API Error): {ex}")

@router.message(F.text)
async def process_natural_language_message(message: types.Message):
    """
    Handler assíncrono que implementa o padrão "Acknowledge & Update".
    Devolve um HTTP 200 pro Telegram em milissegundos para evitar os temidos Timeouts,
    lançando a pesada matemática do LangGraph para as threads paralelas de background.
    """
    logger.info(f">>> Interceptação de Texto (Acknowledge mode): '{message.text}'")

    # 1. Resposta IMEDIATA para matar o ciclo da Webhook e evitar as retentativas fantasma.
    provisional_text = "⏳ *Entendido, Comandante.* Acionando as matrizes de busca e consultando as carteiras de milhas..."
    status_msg = await message.reply(provisional_text, parse_mode="Markdown")
    
    # 2. Transfere todo o peso (Rede, Banco e IA) para uma tarefa background (Fire-and-forget)
    asyncio.create_task(
        process_langgraph_task(
            bot=message.bot,
            chat_id=message.chat.id,
            message_id=status_msg.message_id, # Usamos esse ID para atualizar o balão no futuro
            user_text=message.text
        )
    )
    
    # 3. Retorno instantâneo. Libera o worker do Aiogram.
    return
