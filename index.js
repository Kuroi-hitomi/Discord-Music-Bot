const { Client, GatewayIntentBits, GuildMember } = require("discord.js");
const { Player, QueryType } = require("discord-player");
const config = require("./config.json");

const client = new Client({
    intents: [
        GatewayIntentBits.GuildVoiceStates, 
        GatewayIntentBits.GuildMessages, 
        GatewayIntentBits.Guilds,
        GatewayIntentBits.MessageContent
    ]
});
client.login(config.token);

client.once('ready', async () => {
    console.log('Ready!');

    //Ensure application owner information is fetched
    if (!client.application?.owner)
    {
        await client.application?.fetch()
    }
});

client.on("error", console.error);
client.on("warn", console.warn);

//Create Discord Player
const player = new Player(client);

player.on("error", (queue, error) => {
    console.log(`[${queue.guild.name}] Error emitted from the queue: ${error.message}`);
});

player.on("connectionError", (queue, error) => {
    console.log(`[${queue.guild.name}] Error emitted from the connection: ${error.message}`);
});

player.on("trackStart", (queue, track) => {
    queue.metadata.send(`🎵 | Chandelier started singing: **${track.title}** for you in **${queue.connection.channel.name}**!`);
});

player.on("trackAdd", (queue, track) => {
    queue.metadata.send(`🎵 | Track **${track.title}** queued!`);
});

player.on("botDisconnect", (queue) => {
    queue.metadata.send("❌ | I was manually disconnected from the voice channel, clearing queue!");
});

player.on("channelEmpty", (queue) => {
    queue.metadata.send("❌ | Nobody is in the voice channel, leaving......");
});

player.on("queueEnd", (queue) => {
    queue.metadata.send("✅ | Queue finished!");
});

//Add Slash Commands Function

client.on("messageCreate", async (message) => {
    console.log(`Message received: ${message.content} from ${message.author.tag}.`);
    
    if (message.author.bot || !message.guild) {
        console.log("Message is from a bot or not from a guild. Ignoring.");
        return;
    }
        
    if (message.content === "!deploy" && message.author.id === client.application?.owner?.id) {
        console.log(`Deploy command received from ${message.author.tag}`);

        try 
        {
            await message.guild.commands.set([
                {
                    name: "play",
                    description: "大山老师将会为你高歌此曲，并加入歌曲队列",
                    options: [
                        {
                            name: "song-name",
                            type: 3,
                            description: "歌曲名或Youtube URL",
                            required: true
                        }
                    ]
    
                },
                {
                    name: "skip",
                    description: "大山老师不喜欢这首曲子，并选择跳过"
                },
                {
                    name:"queue",
                    description: "大山老师即将歌唱的所有歌曲"
                },
                {
                    name:"stop",
                    description: "大山老师遗憾的为你闭上了嘴..."
                },     
        ]);
        await message.reply("Deployed!");
        } catch (error) {
            console.error(`Failed to deploy commands: ${error.message}`);
            await message.reply(`Failed to deploy commands: ${error.message}`);
        }


    
    }else if (message.content === "!deploy"){
        console.log(`Unauthorized deploy command attempt by ${message.author.tag}`);

    }

});

client.on("interactionCreate", async (interaction) => {
    if (!interaction.isCommand() || !interaction.guildID) return;

    if (!(interaction.member instanceof GuildMember) || !interaction.member.voice.channel){
        return void interaction.reply({ content: "你都不在频道里，哥们怎么给你唱歌？", ephemeral: true });
    }

    if (interaction.guild.memberCount.voice.channelID && interaction.member.voice.channelID !== interaction.guild.memberCount.voice.channelID) {
        return void interaction.reply({ content: "你跟我在同一个频道里吗？这智商配听我大山唱歌？", ephemeral: true });
    }

    if (interaction.commandName === "play") {
        await interaction.deferReply();

        const query = interaction.options.get("query").value;
        const searchResult = await player.search(query, {
            requestedBy: interaction.user,
            searchEngine: QueryType.AUTO
        }).catch(() => {});
        
        if (!searchResult || !searchResult.tracks.length) return void interaction.followUp({ content: "No results were found!" });

        const queue = await player.createQueue(interaction.guild, {
            metadata: interaction.channel
        });

        try {
            if (!queue.connection) await queue.connect(interaction.member.voice.channel);    
        } catch {
            void player.deleteQueue(interaction.guildID);
            return void interaction.followUp({ content: "Could not join your voice channel!" });
        }

        await interaction.followUp({ content: `⏱ | Loading your ${searchResult.playlist ? "playlist" : "track"}...` });
        searchResult.playlist ? queue.addTracks(searchResult.tracks) : queue.addTrack(searchResult.tracks[0]);
        if (!queue.playing) await queue.play();
    }

    if (interaction.commandName === "skip") {
        await interaction.degerReply();
        const queue = player.getQueue(interaction.guildID);
        if (!queue || !queue.playing) return void interaction.followUp({ content: "❌ | No music is being played!" });
        const currentTrack = queue.current;
        const success = queue.skip();
        return void interaction.followUp({
            content: success ? `✅ | Skipped **${currentTrack}**!` : "❌ | Something went wrong!"
        });
    }

});

