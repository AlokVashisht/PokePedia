import discord
from discord.ext import commands
from discord.ui import Button, View
from fuzzywuzzy import process
import json
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Read Pokémon data from JSON file
with open('pokemonData.json', 'r') as file:
    pokemon_data = json.load(file)

# Define bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='P.', intents=intents)

# Function to fetch Pokémon data from JSON
def fetch_pokemon_data(pokemon_name):
    pokemon_info = pokemon_data.get(pokemon_name.lower())
    return pokemon_info

# Function to fetch moves from PokeAPI
def fetch_pokemon_moves(pokemon_name):
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name.lower()}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return [move['move']['name'] for move in data['moves']]
    else:
        return None

# Function to fetch shiny image from PokeAPI
def fetch_shiny_image_url(pokemon_name):
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name.lower()}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['sprites']['front_shiny']
    else:
        return None

# Function to fetch weaknesses from PokeAPI
def fetch_pokemon_weaknesses(pokemon_name):
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name.lower()}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        types = [t['type']['name'] for t in data['types']]
        weaknesses = {}
        for t in types:
            type_url = f"https://pokeapi.co/api/v2/type/{t}"
            type_response = requests.get(type_url)
            if type_response.status_code == 200:
                type_data = type_response.json()
                damage_relations = type_data['damage_relations']
                weaknesses[t] = {
                    "double_damage_from": [d['name'] for d in damage_relations['double_damage_from']],
                    "half_damage_from": [d['name'] for d in damage_relations['half_damage_from']],
                    "no_damage_from": [d['name'] for d in damage_relations['no_damage_from']],
                }
            else:
                return None
        return weaknesses
    else:
        return None

class PokemonView(View):
    def __init__(self, matched_name):
        super().__init__()
        self.matched_name = matched_name

    @discord.ui.button(label="Moves", style=discord.ButtonStyle.primary, custom_id="moves_button")
    async def moves_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        moves = fetch_pokemon_moves(self.matched_name)
        moves_list = "\n".join(moves) if moves else "Moves data not available."
        embed = self.get_embed(moves_list)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Shiny", style=discord.ButtonStyle.success, custom_id="shiny_button")
    async def shiny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        shiny_image_url = fetch_shiny_image_url(self.matched_name)
        if shiny_image_url:
            embed = discord.Embed(title=f"Shiny form of {self.matched_name.capitalize()}:", color=0xFFD700)
            embed.set_image(url=shiny_image_url)
            await interaction.response.edit_message(embed=embed)
        else:
            await interaction.response.send_message("Shiny image not available.", ephemeral=True)

    @discord.ui.button(label="Weaknesses", style=discord.ButtonStyle.danger, custom_id="weaknesses_button")
    async def weaknesses_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        weaknesses = fetch_pokemon_weaknesses(self.matched_name)
        if weaknesses:
            weaknesses_text = await self.format_weaknesses(weaknesses)
            embed = discord.Embed(title=f"Weaknesses for {self.matched_name.capitalize()}:", description=weaknesses_text, color=0xFF0000)
            await interaction.response.edit_message(embed=embed)
        else:
            await interaction.response.send_message("Weaknesses data not available.", ephemeral=True)

    async def format_weaknesses(self, weaknesses):
        text = "**Weak**\n"
        for weakness_type, damage_relations in weaknesses.items():
            if damage_relations["double_damage_from"]:
                text += f"{', '.join(damage_relations['double_damage_from'])}\n"
        text += "**Neutral**\n"
        for weakness_type, damage_relations in weaknesses.items():
            if damage_relations["half_damage_from"]:
                text += f"{', '.join(damage_relations['half_damage_from'])}\n"
        text += "**Immune**\n"
        for weakness_type, damage_relations in weaknesses.items():
            if damage_relations["no_damage_from"]:
                text += f"{', '.join(damage_relations['no_damage_from'])}\n"
        return text

    def get_embed(self, text):
        embed = discord.Embed(title=self.matched_name.capitalize(), description=text, color=0xFFFF00)
        return embed

# Command to fetch Pokémon info
@bot.command(name='d')
async def d(ctx, *, pokemon_name: str):
    best_match = process.extractOne(pokemon_name, list(pokemon_data.keys()))
    if best_match:
        matched_name = best_match[0]
        data = fetch_pokemon_data(matched_name)
        if data:
            species_data_url = f"https://pokeapi.co/api/v2/pokemon-species/{matched_name.lower()}"
            species_data_response = requests.get(species_data_url)
            if species_data_response.status_code == 200:
                species_data = species_data_response.json()
                rarity = "Legendary" if species_data['is_legendary'] else "Mythical" if species_data['is_mythical'] else "Common"
                evolution_chain_url = species_data['evolution_chain']['url']
                evolution_chain_data = requests.get(evolution_chain_url).json()
                evolution_chain = parse_evolution_chain(evolution_chain_data)
            else:
                rarity = "Unknown"
                evolution_chain = "Unknown"

            embed = discord.Embed(title=data['name'], description=f"ID: {data['num']}", color=0xFFFF00)
            embed.add_field(name="Height", value=f"{data['heightm']} m")
            embed.add_field(name="Weight", value=f"{data['weightkg']} kg")
            embed.add_field(name="Stats", value="\n".join([
                f"❤️ HP: {data['baseStats']['hp']}",
                f"⚔️ ATK: {data['baseStats']['atk']}",
                f"🛡️ DEF: {data['baseStats']['def']}",
                f"⚔️ SPATK: {data['baseStats']['spa']}",
                f"🛡️ SPDEF: {data['baseStats']['spd']}",
                f"👟 SPEED: {data['baseStats']['spe']}"
            ]), inline=False)
            embed.add_field(name="Types", value=", ".join(data['types']))
            embed.add_field(name="Rarity", value=rarity)
            embed.add_field(name="Evolution Chain", value=evolution_chain, inline=False)
            embed.set_image(url=f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{data['num']}.png")
            await ctx.send(embed=embed, view=PokemonView(matched_name))
        else:
            await ctx.send("Could not fetch data. Please try again.")
    else:
        await ctx.send("No matching Pokémon found.")

# Function to parse the evolution chain data
def parse_evolution_chain(chain):
    evolutions = []
    current = chain['chain']
    while current:
        evolutions.append(current['species']['name'])
        if current['evolves_to']:
            current = current['evolves_to'][0]
        else:
            break
    return " -> ".join(evolutions)

# Run the bot
bot.run(TOKEN)
